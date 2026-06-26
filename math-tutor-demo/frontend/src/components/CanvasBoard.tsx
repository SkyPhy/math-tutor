import React, {
    useEffect,
    useRef,
    useImperativeHandle,
    forwardRef,
    useCallback,
} from 'react';
import { MathResponse } from '../types';

export interface CanvasBoardRef {
    getCanvasBlob: () => Promise<Blob | null>;
}

interface CanvasBoardProps {
    // Kept for backwards-compat with App.tsx; now hands back the raw <canvas>.
    setCanvasRef: (ref: HTMLCanvasElement | null) => void;
    result: MathResponse | null;
}

const CANVAS_W = 800;
const CANVAS_H = 600;

/**
 * Freehand drawing board backed by a native <canvas> 2-D context.
 *
 * This used to be built on react-p5 + p5.js instance mode, where every frame
 * blitted an offscreen createGraphics() buffer. That pipeline failed to paint
 * (strokes never appeared on defaultCanvas0), so we drive the canvas directly:
 * the 2-D context is persistent, so committed strokes simply stay on screen.
 */
const CanvasBoard = forwardRef<CanvasBoardRef, CanvasBoardProps>(({ setCanvasRef, result }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const isDrawing = useRef(false);
    const lastPoint = useRef<{ x: number; y: number } | null>(null);

    // AI "typewriter" animation bookkeeping.
    const animTimer = useRef<number | null>(null);
    const animX = useRef(20);

    useImperativeHandle(ref, () => ({
        getCanvasBlob: () =>
            new Promise<Blob | null>((resolve) => {
                const canvas = canvasRef.current;
                if (!canvas) return resolve(null);
                canvas.toBlob((blob) => resolve(blob), 'image/png');
            }),
    }));

    const getCtx = () => canvasRef.current?.getContext('2d') ?? null;

    const paintBackground = useCallback(() => {
        const ctx = getCtx();
        if (!ctx) return;
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
    }, []);

    // Initialise the white board once the canvas mounts.
    useEffect(() => {
        setCanvasRef(canvasRef.current);
        paintBackground();
        return () => {
            if (animTimer.current !== null) window.clearInterval(animTimer.current);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Map a pointer event to canvas-internal coordinates (handles CSS scaling).
    const toCanvasPoint = (clientX: number, clientY: number) => {
        const canvas = canvasRef.current!;
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        return {
            x: (clientX - rect.left) * scaleX,
            y: (clientY - rect.top) * scaleY,
        };
    };

    const strokeFrom = (from: { x: number; y: number }, to: { x: number; y: number }) => {
        const ctx = getCtx();
        if (!ctx) return;
        ctx.strokeStyle = '#0f172a';
        ctx.lineWidth = 3;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.stroke();
    };

    const startDrawing = (clientX: number, clientY: number) => {
        isDrawing.current = true;
        const p = toCanvasPoint(clientX, clientY);
        lastPoint.current = p;
        // Dot so a single click/tap leaves a mark.
        const ctx = getCtx();
        if (ctx) {
            ctx.fillStyle = '#0f172a';
            ctx.beginPath();
            ctx.arc(p.x, p.y, 1.5, 0, Math.PI * 2);
            ctx.fill();
        }
    };

    const moveDrawing = (clientX: number, clientY: number) => {
        if (!isDrawing.current || !lastPoint.current) return;
        const p = toCanvasPoint(clientX, clientY);
        strokeFrom(lastPoint.current, p);
        lastPoint.current = p;
    };

    const endDrawing = () => {
        isDrawing.current = false;
        lastPoint.current = null;
    };

    // ── Mouse handlers ──
    const onMouseDown = (e: React.MouseEvent) => startDrawing(e.clientX, e.clientY);
    const onMouseMove = (e: React.MouseEvent) => moveDrawing(e.clientX, e.clientY);
    const onMouseUp = () => endDrawing();
    const onMouseLeave = () => endDrawing();

    // ── Touch handlers ──
    const onTouchStart = (e: React.TouchEvent) => {
        e.preventDefault();
        const t = e.touches[0];
        startDrawing(t.clientX, t.clientY);
    };
    const onTouchMove = (e: React.TouchEvent) => {
        e.preventDefault();
        const t = e.touches[0];
        moveDrawing(t.clientX, t.clientY);
    };
    const onTouchEnd = (e: React.TouchEvent) => {
        e.preventDefault();
        endDrawing();
    };

    const clearCanvas = () => {
        if (animTimer.current !== null) {
            window.clearInterval(animTimer.current);
            animTimer.current = null;
        }
        paintBackground();
    };

    // AI typewriter: when a result arrives, "write" the equation onto the board.
    const triggerAIWriting = useCallback((text: string) => {
        const ctx = getCtx();
        if (!ctx || !text) return;
        if (animTimer.current !== null) window.clearInterval(animTimer.current);

        // Strip $-delimiters so LaTeX reads as a plain caption.
        const chars = text.replace(/\$/g, '').split('');
        let i = 0;
        animX.current = 20;
        const y = 40;

        ctx.font = '28px "JetBrains Mono", monospace';
        ctx.textBaseline = 'middle';
        ctx.textAlign = 'left';
        ctx.fillStyle = '#38bdf8';

        animTimer.current = window.setInterval(() => {
            if (i >= chars.length) {
                if (animTimer.current !== null) window.clearInterval(animTimer.current);
                animTimer.current = null;
                return;
            }
            const ch = chars[i++];
            ctx.fillText(ch, animX.current, y);
            animX.current += ctx.measureText(ch).width;
        }, 45);
    }, []);

    useEffect(() => {
        if (result) triggerAIWriting(result.latex || result.original);
    }, [result, triggerAIWriting]);

    return (
        <div
            id="canvas-wrapper"
            className="glass-panel"
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, padding: 20 }}
        >
            <div
                id="canvas-container"
                style={{ borderRadius: 16, overflow: 'hidden', boxShadow: '0 10px 30px rgba(0,0,0,0.1)' }}
            >
                <canvas
                    ref={canvasRef}
                    width={CANVAS_W}
                    height={CANVAS_H}
                    style={{
                        display: 'block',
                        background: '#ffffff',
                        touchAction: 'none',
                        cursor: 'crosshair',
                        maxWidth: '100%',
                    }}
                    onMouseDown={onMouseDown}
                    onMouseMove={onMouseMove}
                    onMouseUp={onMouseUp}
                    onMouseLeave={onMouseLeave}
                    onTouchStart={onTouchStart}
                    onTouchMove={onTouchMove}
                    onTouchEnd={onTouchEnd}
                />
            </div>
            <div style={{ marginTop: 15, display: 'flex', gap: 10 }}>
                <button className="btn-secondary" onClick={clearCanvas}>Clear Board</button>
            </div>
        </div>
    );
});

export default CanvasBoard;
