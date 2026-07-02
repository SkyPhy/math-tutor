"""
Handwriting recognition — nex-n2-pro (OpenAI-compatible vision)
================================================================
Turns a whiteboard snapshot (PNG bytes) into a math expression string.

The student draws on the canvas and presses **Submit**; the frontend posts the
PNG here. We preprocess the image (crop/upscale/thicken the ink), send it to the
`nex-n2-pro` vision model via an OpenAI-compatible `/chat/completions` endpoint,
and return the transcribed *text* — that text (not the picture) is what gets
forwarded into the analyze pipeline.

This replaces the old local EasyOCR model: no torch, no model download, just an
HTTP call configured by NEX_OCR_* in `.env` (see config.py / .env.example). If
the gateway is not configured, `recognize_image` returns "" so the caller can
fall back to a friendly placeholder instead of crashing.

Uses only the standard library (urllib) — no extra pip dependency.
"""

from __future__ import annotations

import io
import re
import json
import base64
import socket
import urllib.request
import urllib.error
from typing import List

from . import config


# The instruction we give the vision model. The student's whiteboard holds a full
# worked solution — not just a bare formula — so we transcribe EVERYTHING (maths,
# symbols, AND any English/Chinese words) and PRESERVE the line breaks, because the
# 校对屏 shows this text for the student to correct and the layout carries meaning.
_OCR_PROMPT = (
    "You are an OCR transcriber for a student's handwritten work. Transcribe "
    "EVERYTHING written in the image — mathematics, symbols, AND any natural-language "
    "text, whether English or Chinese — exactly as written. "
    "PRESERVE the line breaks: put each written line on its own line, in reading order. "
    "In maths use ^ for exponents and * for multiplication. "
    "Do NOT insert spaces between the digits of a number or the letters of a word. "
    "Output ONLY the transcription as plain text — no explanation, no commentary, "
    "no code fences, no $ delimiters. If the image is blank, output nothing."
)


def _clean_transcription(fragments: List[str]) -> str:
    """
    Lightly normalise the raw OCR output while KEEPING the student's line breaks.

    Unlike the old bare-expression cleaner, we no longer collapse all whitespace —
    the transcription now includes prose (English/Chinese) and multi-line working,
    so newlines and word spaces must survive. We only: join content parts, strip
    code fences the model may add, normalise line endings, and tidy each line
    (collapse runs of ≥2 spaces, trim trailing spaces). The 校对屏 lets the student
    fix anything the OCR got wrong.
    """
    text = "".join(f for f in fragments if f)

    # Strip code fences the model sometimes adds despite the prompt.
    text = text.replace("```", "")
    # Normalise line endings so downstream sees plain "\n".
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Per line: collapse only runs of ≥2 spaces/tabs (keep single word spaces),
    # trim trailing whitespace. Newlines are preserved verbatim.
    lines = [re.sub(r"[ \t]{2,}", " ", ln).rstrip() for ln in text.split("\n")]
    # Drop blank lines at the very top/bottom, keep internal ones.
    return "\n".join(lines).strip("\n")


def _preprocess(image_bytes: bytes) -> bytes:
    """
    Make a sparse whiteboard drawing easier to read.

    The frontend canvas is a large (800×600) mostly-white board with thin 3px
    black pen strokes. We crop to the ink, pad, upscale, and thicken the strokes
    so faint pen lines read as solid characters. Returns PNG bytes; falls back to
    the original bytes if anything goes wrong or the board is effectively blank.
    """
    from PIL import Image, ImageOps, ImageFilter  # local import keeps load light

    img = Image.open(io.BytesIO(image_bytes)).convert("L")  # grayscale

    # Bounding box of the ink: invert (ink → white) so getbbox() finds it.
    inverted = ImageOps.invert(img)
    bbox = inverted.getbbox()
    if bbox is None:
        return image_bytes  # nothing drawn

    pad = 40
    left = max(bbox[0] - pad, 0)
    top = max(bbox[1] - pad, 0)
    right = min(bbox[2] + pad, img.width)
    bottom = min(bbox[3] + pad, img.height)
    cropped = img.crop((left, top, right, bottom))

    # Upscale so the content is a reasonable size for the detector.
    target_h = 160
    if cropped.height < target_h:
        scale = target_h / cropped.height
        new_w = max(int(cropped.width * scale), 1)
        cropped = cropped.resize((new_w, target_h), Image.LANCZOS)

    # Cap the width so a very wide drawing doesn't balloon the payload.
    max_w = 1600
    if cropped.width > max_w:
        scale = max_w / cropped.width
        new_h = max(int(cropped.height * scale), 1)
        cropped = cropped.resize((max_w, new_h), Image.LANCZOS)

    # Thicken dark strokes: MinFilter spreads the darker (ink) pixels.
    thick = cropped.filter(ImageFilter.MinFilter(3))

    out = thick.convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def _call_openai_ocr(png_bytes: bytes, *, endpoint: str, api_key: str, model: str,
                     max_tokens: int, timeout: float, engine: str,
                     disable_thinking: bool = False) -> str:
    """POST the image to ANY OpenAI-compatible chat-completions endpoint as an
    image_url and return the transcribed text. Shared by every OpenAI-protocol OCR
    engine (nex-n2-pro, DeepSeek vision, …). Raises on transport/HTTP/parse failure.

    `disable_thinking` sends `chat_template_kwargs.enable_thinking=false` — needed
    for reasoning models (nex-n2-pro) whose UNBOUNDED "thinking" otherwise blows the
    timeout and returns empty content; harmless for non-reasoning vision models."""
    data_url = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _OCR_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    }
    if disable_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}",
    }
    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    obj = json.loads(raw)

    # OpenAI-compatible: choices[0].message.content (string, or content parts).
    choices = obj.get("choices") or []
    if not choices:
        return ""
    choice = choices[0]
    msg = choice.get("message", {})
    content = msg.get("content", "")
    if isinstance(content, list):
        # Some gateways return content as a list of parts.
        content = "".join(
            p.get("text", "") for p in content if isinstance(p, dict)
        )
    content = content if isinstance(content, str) else ""

    # If `content` is empty AND the model was cut off mid-thought
    # (finish_reason == "length"), the token budget was too small — surface it in
    # the log so it isn't a silent blank read (especially for reasoning models).
    if not content.strip() and choice.get("finish_reason") == "length":
        print(f"[recognize] {engine} ran out of tokens before answering "
              f"(finish_reason=length). Raise its MAX_TOKENS in .env.")
    return content


def _call_nex_ocr(png_bytes: bytes) -> str:
    """Transcribe via the nex-n2-pro vision endpoint (path 1)."""
    return _call_openai_ocr(
        png_bytes, endpoint=config.ocr_endpoint(), api_key=config.NEX_OCR_API_KEY,
        model=config.NEX_OCR_MODEL, max_tokens=config.NEX_OCR_MAX_TOKENS,
        timeout=config.NEX_OCR_TIMEOUT, engine="nex-n2-pro", disable_thinking=True,
    )


def _call_deepseek_ocr(png_bytes: bytes) -> str:
    """Transcribe via a DeepSeek (OpenAI-compatible) VISION endpoint (path 3)."""
    return _call_openai_ocr(
        png_bytes,
        endpoint=config.openai_chat_endpoint(config.DEEPSEEK_OCR_BASE_URL),
        api_key=config.DEEPSEEK_OCR_API_KEY, model=config.DEEPSEEK_OCR_MODEL,
        max_tokens=config.DEEPSEEK_OCR_MAX_TOKENS, timeout=config.DEEPSEEK_OCR_TIMEOUT,
        engine="deepseek-vision",
    )


# ── Path 2: send the drawing straight to the general AI (Claude vision) ──────
# The design offers two ways to turn whiteboard ink into text:
#   1. render → nex-n2-pro specialised OCR (the default above), and
#   2. hand the drawing directly to the general AI.
# This is path 2: post the PNG to the Anthropic-compatible Messages API as an
# image block. Useful as an alternative/fallback engine when nex is unconfigured,
# slow, or returns nothing. Reuses the Claude gateway config (CLAUDE_*).

def claude_vision_available() -> bool:
    """True when the Claude gateway (used as a vision OCR fallback) is configured."""
    return config.is_configured()


def _call_claude_vision(png_bytes: bytes) -> str:
    """POST the image to the Claude Messages API as an image block and return the
    transcribed text. Raises on any transport/HTTP/parse failure."""
    b64 = base64.b64encode(png_bytes).decode("ascii")
    payload = {
        "model": config.CLAUDE_DEFAULT_MODEL,
        "max_tokens": 512,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64",
                                                 "media_type": "image/png", "data": b64}},
                    {"type": "text", "text": _OCR_PROMPT},
                ],
            }
        ],
    }
    headers = {
        "content-type": "application/json",
        "anthropic-version": config.CLAUDE_ANTHROPIC_VERSION,
    }
    if config.CLAUDE_AUTH_HEADER == "authorization":
        headers["authorization"] = f"Bearer {config.CLAUDE_API_KEY}"
    else:
        headers["x-api-key"] = config.CLAUDE_API_KEY

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        config.CLAUDE_BASE_URL + "/v1/messages", data=body, headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=config.CLAUDE_TIMEOUT) as resp:
        obj = json.loads(resp.read().decode("utf-8"))

    # Anthropic Messages: content is a list of blocks; concat the text ones.
    content = obj.get("content") if isinstance(obj, dict) else None
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content
                       if isinstance(b, dict) and b.get("type") == "text")
    return ""


def recognize_via_claude(image_bytes: bytes) -> dict:
    """Path-2 recognition: transcribe handwriting with Claude vision instead of
    nex OCR. Same {"text", "status"} contract as recognize_detailed()."""
    if not config.is_configured():
        return {"text": "", "status": "unconfigured"}
    try:
        png_bytes = _preprocess(image_bytes)
    except Exception:
        png_bytes = image_bytes
    try:
        raw = _call_claude_vision(png_bytes)
    except (TimeoutError, socket.timeout):
        print("[recognize] Claude vision timed out.")
        return {"text": "", "status": "timeout"}
    except urllib.error.URLError as e:
        if isinstance(getattr(e, "reason", None), (TimeoutError, socket.timeout)):
            return {"text": "", "status": "timeout"}
        print(f"[recognize] Claude vision error: {e}")
        return {"text": "", "status": "error"}
    except (urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"[recognize] Claude vision error: {e}")
        return {"text": "", "status": "error"}
    except Exception as e:
        print(f"[recognize] Claude vision unexpected error: {e}")
        return {"text": "", "status": "error"}
    text = _clean_transcription([raw])
    return {"text": text, "status": "ok" if text else "empty"}


def list_models() -> dict:
    """Advertise the OCR engines the select screen can pick from.

    Each model maps to a ``method`` value accepted by ``POST /recognize``:
      - ``nex``    → the nex-n2-pro specialised OCR (path 1, default)
      - ``claude`` → Claude vision (path 2)
      - ``auto``   → nex first, fall back to Claude if it reads nothing
    ``available`` reflects whether the backing gateway is configured in ``.env``;
    the UI still lists every engine but can flag/disable the unusable ones. The
    default is the first usable engine so the dropdown lands on something that works.
    """
    nex_ok = config.ocr_configured()
    claude_ok = claude_vision_available()
    deepseek_ok = deepseek_vision_available()
    models = [
        {"id": "nex", "label": "nex-n2-pro 专用 OCR", "available": nex_ok},
        {"id": "deepseek", "label": "DeepSeek 视觉", "available": deepseek_ok},
        {"id": "claude", "label": "Claude 视觉", "available": claude_ok},
        {"id": "auto", "label": "自动（nex 失败回退 Claude）", "available": nex_ok or claude_ok},
    ]
    if nex_ok:
        default = "nex"
    elif deepseek_ok:
        default = "deepseek"
    elif claude_ok:
        default = "claude"
    else:
        default = "nex"  # nothing configured → mock path; keep a stable default
    return {"models": models, "default": default}


def warmup() -> bool:
    """No local model to preload (OCR is a remote API now). Kept for the
    startup hook's call site; returns whether the OCR gateway is configured."""
    return config.ocr_configured()


def _run_openai_ocr(image_bytes: bytes, caller, engine: str) -> dict:
    """Preprocess the image, call one OpenAI-compatible OCR `caller`, and map the
    outcome to the shared {"text", "status"} contract. Used by every OpenAI-protocol
    OCR engine (nex-n2-pro, DeepSeek vision) so they share one failure ladder."""
    try:
        png_bytes = _preprocess(image_bytes)
    except Exception:
        png_bytes = image_bytes  # fall back to the raw upload

    try:
        raw = caller(png_bytes)
    except (TimeoutError, socket.timeout):
        print(f"[recognize] {engine} timed out (gateway slow/congested).")
        return {"text": "", "status": "timeout"}
    except urllib.error.URLError as e:
        # A read timeout often surfaces here wrapping a socket timeout.
        if isinstance(getattr(e, "reason", None), (TimeoutError, socket.timeout)):
            return {"text": "", "status": "timeout"}
        print(f"[recognize] {engine} gateway error: {e}")
        return {"text": "", "status": "error"}
    except (urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"[recognize] {engine} gateway error: {e}")
        return {"text": "", "status": "error"}
    except Exception as e:
        print(f"[recognize] {engine} unexpected error: {e}")
        return {"text": "", "status": "error"}

    text = _clean_transcription([raw])
    return {"text": text, "status": "ok" if text else "empty"}


def recognize_detailed(image_bytes: bytes) -> dict:
    """
    Recognise the handwritten math via nex-n2-pro, returning {"text", "status"} so
    the caller can tell apart the failure modes (which all look like "" otherwise):

      status: "ok"           — got a transcription
              "empty"        — gateway answered but read no legible math
              "timeout"      — gateway too slow (congested); worth retrying
              "error"        — transport/HTTP/parse failure
              "unconfigured" — no OCR gateway in .env
    """
    if not config.ocr_configured():
        return {"text": "", "status": "unconfigured"}
    return _run_openai_ocr(image_bytes, _call_nex_ocr, "nex-n2-pro")


def deepseek_vision_available() -> bool:
    """True when the DeepSeek OCR (vision) endpoint is configured in .env."""
    return config.deepseek_ocr_configured()


def recognize_via_deepseek(image_bytes: bytes) -> dict:
    """Path-3 recognition: transcribe handwriting with a DeepSeek (OpenAI-compatible)
    VISION model. Same {"text", "status"} contract as recognize_detailed()."""
    if not config.deepseek_ocr_configured():
        return {"text": "", "status": "unconfigured"}
    return _run_openai_ocr(image_bytes, _call_deepseek_ocr, "deepseek-vision")


def recognize_image(image_bytes: bytes) -> str:
    """Backwards-compatible string API: just the recognised text ("" on any
    failure). Prefer recognize_detailed() when the failure reason matters."""
    return recognize_detailed(image_bytes).get("text", "")


def is_available() -> bool:
    """True when the OCR gateway is configured and usable."""
    return config.ocr_configured()
