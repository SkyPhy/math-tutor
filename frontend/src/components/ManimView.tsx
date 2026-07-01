import { useEffect, useState } from 'react';
import { manimRender } from '../api';
import { API_BASE } from '../config';
import { useMathJax } from '../hooks/useMathJax';
import type { ManimFrame, ManimRenderResp } from '../types';

// ④ 助手屏 / ⑤ 答疑屏 <manim> block (v0.4.5b, extended v0.4.6). A line-analysis or a
// chat reply may attach a storyboard note OR raw Manim code; this turns it into an
// actual animation on demand: POST /manim/render returns a real MP4 when the server
// has Manim CE + ffmpeg, otherwise it degrades to a browser storyboard (frames
// stepped through in-page) — so the affordance never errors out ("无 Manim 时自动回落
// 且不报错").
//
// `spec` = a natural-language description of the animation; `code` = ready Manim CE
// source (rendered as-is when present). Pass one or the other.
export function ManimView({ spec, code, expression }: { spec?: string; code?: string; expression: string }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ManimRenderResp | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const label = (spec || '形象化演示').trim();

  const run = async () => {
    setOpen(true);
    if (loading) return;
    setLoading(true);
    setErr(null);
    try {
      const res = await manimRender({ expression, spec, manim_code: code });
      setData(res);
    } catch (e) {
      setErr('生成失败：' + (e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="manim-block">
      <div className="manim-head">
        <span className="manim-spec">🎬 {label}</span>
        {!open || err ? (
          <button className="chip-btn manim-run" onClick={run} disabled={loading}>
            {loading ? '生成中…' : data ? '重新生成' : '▶ 生成动画'}
          </button>
        ) : null}
      </div>

      {loading ? <p className="manim-note">正在生成动画（首次可能较慢）…</p> : null}
      {err ? <p className="select-err">{err}</p> : null}

      {data ? <ManimResult data={data} /> : null}
    </div>
  );
}

function ManimResult({ data }: { data: ManimRenderResp }) {
  if (data.status === 'ok' && data.video_url) {
    return (
      <div className="manim-video-wrap">
        <video className="manim-video" src={API_BASE + data.video_url} controls autoPlay loop muted />
      </div>
    );
  }
  // Degraded: animate the storyboard in-page. Honest about why there is no real video.
  const frames = data.storyboard || [];
  return (
    <div className="manim-fallback">
      <p className="manim-note">{data.reason || '未生成真视频，改用浏览器故事板演示。'}</p>
      {frames.length > 0 ? (
        <Storyboard frames={frames} />
      ) : (
        <p className="manim-note">（暂无可演示的故事板帧。）</p>
      )}
      {data.manim_code ? (
        <details className="manim-code">
          <summary>查看生成的 Manim 代码（可本地 `manim -ql` 渲染）</summary>
          <pre>
            <code>{data.manim_code}</code>
          </pre>
        </details>
      ) : null}
    </div>
  );
}

// In-page storyboard player: step through the frames, auto-advancing while playing.
function Storyboard({ frames }: { frames: ManimFrame[] }) {
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(true);

  const clamped = Math.min(step, frames.length - 1);
  const frame = frames[clamped];

  useEffect(() => {
    if (!playing) return;
    const id = window.setTimeout(() => {
      setStep((s) => (s + 1 < frames.length ? s + 1 : s));
      if (clamped + 1 >= frames.length - 1) setPlaying(false);
    }, 1600);
    return () => window.clearTimeout(id);
  }, [clamped, playing, frames.length]);

  const ref = useMathJax<HTMLDivElement>(frame?.latex);

  return (
    <div className="storyboard">
      <div className="storyboard-stage">
        {frame?.title ? <div className="storyboard-title">{frame.title}</div> : null}
        <div className="storyboard-math" ref={ref}>
          {frame?.latex ? `\\[ ${frame.latex} \\]` : ''}
        </div>
        {frame?.caption ? <div className="storyboard-caption">{frame.caption}</div> : null}
      </div>
      <div className="storyboard-controls">
        <button className="tool-btn" onClick={() => { setPlaying(false); setStep((s) => Math.max(0, s - 1)); }} disabled={clamped === 0}>
          ‹ 上一步
        </button>
        <span className="storyboard-count">{clamped + 1} / {frames.length}</span>
        <button className="tool-btn" onClick={() => { setPlaying(false); setStep((s) => Math.min(frames.length - 1, s + 1)); }} disabled={clamped >= frames.length - 1}>
          下一步 ›
        </button>
        <button className="tool-btn" onClick={() => { setStep(0); setPlaying(true); }}>↻ 重播</button>
      </div>
    </div>
  );
}
