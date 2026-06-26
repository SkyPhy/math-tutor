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


# The instruction we give the vision model. Kept terse and strict so it returns
# a bare expression, not prose, that SymPy can parse downstream.
_OCR_PROMPT = (
    "You are an OCR engine for handwritten mathematics. Transcribe the single "
    "math expression or equation written in this image. Output ONLY the "
    "expression itself as plain text — no explanation, no surrounding words, no "
    "LaTeX delimiters, no code fences, no $ signs. Use ^ for exponents and * for "
    "multiplication. If the image contains no legible math, output nothing."
)


def _clean_math_text(fragments: List[str]) -> str:
    """
    Normalise raw OCR output into something SymPy-friendly.

    Vision models occasionally wrap the answer in $...$, backticks, or LaTeX,
    and use unicode math glyphs; we strip/convert the math-safe ones.
    """
    text = " ".join(f.strip() for f in fragments if f and f.strip())

    # Strip code fences / LaTeX delimiters the model adds despite the prompt.
    text = text.replace("```", "")
    text = text.replace("$", "")              # $$ x $$ / $ x $ → x
    text = text.strip("`").strip()
    text = re.sub(r"\\[\(\[\)\]]", "", text)  # \( \) \[ \] anywhere
    text = re.sub(r"\\text\s*\{([^}]*)\}", r"\1", text)  # \text{...} → ...

    # LaTeX operator commands → ASCII (do before stripping backslashes).
    latex_ops = {
        "\\times": "*", "\\cdot": "*", "\\div": "/",
        "\\left": "", "\\right": "", "\\,": " ", "\\;": " ",
    }
    for bad, good in latex_ops.items():
        text = text.replace(bad, good)

    # Common glyph confusions / unicode math symbols.
    replacements = {
        "×": "*", "·": "*", "÷": "/",
        "−": "-", "—": "-", "–": "-",   # unicode dashes → ASCII hyphen
        "^": "**",                       # caret power → python power
        "“": "", "”": "", "’": "'",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # nex-n2-pro (esp. with thinking off) tends to space out EVERY character,
    # e.g. "2 x + 3 y - 7 = 1 5". A single expression never needs spaces, and
    # leaving "1 5" would misparse as two numbers — so remove ALL whitespace.
    text = re.sub(r"\s+", "", text).strip()
    return text


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


def _call_nex_ocr(png_bytes: bytes) -> str:
    """POST the image to the nex-n2-pro chat-completions endpoint and return the
    transcribed text. Raises on any transport/HTTP/parse failure."""
    data_url = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
    payload = {
        "model": config.NEX_OCR_MODEL,
        "max_tokens": config.NEX_OCR_MAX_TOKENS,
        "temperature": 0,
        # nex-n2-pro is a reasoning model whose "thinking" is UNBOUNDED — on a
        # busy expression it can reason for 40–120s+ and blow the timeout,
        # returning empty content. OCR needs no chain-of-thought, so disable
        # thinking: this cuts latency dramatically and makes content reliable.
        "chat_template_kwargs": {"enable_thinking": False},
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
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {config.NEX_OCR_API_KEY}",
    }
    req = urllib.request.Request(
        config.ocr_endpoint(), data=body, headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=config.NEX_OCR_TIMEOUT) as resp:
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

    # nex-n2-pro is a reasoning model. If `content` is empty AND the model was
    # cut off mid-thought (finish_reason == "length"), the token budget was too
    # small — surface that clearly in the log so it's not a silent blank read.
    if not content.strip() and choice.get("finish_reason") == "length":
        print("[recognize] nex-n2-pro ran out of tokens before answering "
              "(finish_reason=length). Raise NEX_OCR_MAX_TOKENS in .env.")
    return content


def warmup() -> bool:
    """No local model to preload (OCR is a remote API now). Kept for the
    startup hook's call site; returns whether the OCR gateway is configured."""
    return config.ocr_configured()


def recognize_detailed(image_bytes: bytes) -> dict:
    """
    Recognise the handwritten math, returning {"text", "status"} so the caller
    can tell apart the failure modes (which all look like "" otherwise):

      status: "ok"           — got a transcription
              "empty"        — gateway answered but read no legible math
              "timeout"      — gateway too slow (congested); worth retrying
              "error"        — transport/HTTP/parse failure
              "unconfigured" — no OCR gateway in .env
    """
    if not config.ocr_configured():
        return {"text": "", "status": "unconfigured"}

    try:
        png_bytes = _preprocess(image_bytes)
    except Exception:
        png_bytes = image_bytes  # fall back to the raw upload

    try:
        raw = _call_nex_ocr(png_bytes)
    except (TimeoutError, socket.timeout):
        print("[recognize] nex-n2-pro timed out (gateway slow/congested).")
        return {"text": "", "status": "timeout"}
    except urllib.error.URLError as e:
        # A read timeout often surfaces here wrapping a socket timeout.
        if isinstance(getattr(e, "reason", None), (TimeoutError, socket.timeout)):
            return {"text": "", "status": "timeout"}
        print(f"[recognize] gateway error: {e}")
        return {"text": "", "status": "error"}
    except (urllib.error.HTTPError, json.JSONDecodeError) as e:
        print(f"[recognize] gateway error: {e}")
        return {"text": "", "status": "error"}
    except Exception as e:
        print(f"[recognize] unexpected error: {e}")
        return {"text": "", "status": "error"}

    text = _clean_math_text([raw])
    return {"text": text, "status": "ok" if text else "empty"}


def recognize_image(image_bytes: bytes) -> str:
    """Backwards-compatible string API: just the recognised text ("" on any
    failure). Prefer recognize_detailed() when the failure reason matters."""
    return recognize_detailed(image_bytes).get("text", "")


def is_available() -> bool:
    """True when the OCR gateway is configured and usable."""
    return config.ocr_configured()
