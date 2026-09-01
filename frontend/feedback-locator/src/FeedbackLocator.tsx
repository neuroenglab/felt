import React, { useCallback, useRef, useState, useEffect } from "react";

// ---------------------------------------------------------------------------
// Types (Synced with your requested schema)
// ---------------------------------------------------------------------------
export type ChosenPointsDict = { row: number[]; col: number[] };
export type ImageSize = { w: number; h: number };
export type SegmentSizePx = { w: number; h: number };

export type SensationLocation = {
    image_path: string;
    image_size: ImageSize;
    segment_size_px: SegmentSizePx;
    coarsenessPercent: number;
    chosenPoints: ChosenPointsDict;
};

export type FeedbackLocatorProps = {
    imageSrc: string;
    feedbackLocation?: SensationLocation;
    onUpdate: (location: SensationLocation) => void;
    coarseness?: number;
};

// ---------------------------------------------------------------------------
// Helper Logic
// ---------------------------------------------------------------------------
function getGridFromCoarseness(
    coarsenessPercent: number,
    width: number,
    height: number
): { rows: number; cols: number } {
    if (!(width > 0 && height > 0)) return { rows: 1, cols: 1 };
    const minSide = Math.min(width, height);
    const maxDivisions = Math.min(64, Math.max(2, Math.floor(minSide / 4)));
    const t = Math.max(0, Math.min(1, coarsenessPercent / 100));
    const n = t <= 0 ? 1 : Math.max(1, Math.round(1 + t * (maxDivisions - 1)));
    const aspect = height / width;
    const cols = Math.max(1, Math.round(n * Math.sqrt(1 / aspect)));
    const rows = Math.max(1, Math.round(n * Math.sqrt(aspect)));
    return { rows, cols };
}

const DEFAULT_COARSNESS = 90;

export const FeedbackLocator: React.FC<FeedbackLocatorProps> = ({
    imageSrc,
    feedbackLocation,
    onUpdate,
    coarseness: coarsenessProp = DEFAULT_COARSNESS
}) => {
    const imgRef = useRef<HTMLImageElement>(null);
    const [boundary, setBoundary] = useState<{ width: number; height: number } | null>(null);
    const [eraseMode, setEraseMode] = useState(false);
    const isDrawingRef = useRef(false);
    const isErasingRef = useRef(false);
    const maskDataRef = useRef<Uint8Array | null>(null);
    const maskSizeRef = useRef({ w: 0, h: 0 });
    const [brushRadiusCells, setBrushRadiusCells] = useState(3);
    const [cursorPos, setCursorPos] = useState<{ x: number; y: number } | null>(null);

    // Derive state from props
    const coarsenessPercent = feedbackLocation?.coarsenessPercent ?? coarsenessProp;
    const chosenPoints: ChosenPointsDict = feedbackLocation?.chosenPoints ?? { row: [], col: [] };

    // Use feedbackLocation size if available, otherwise current measured boundary
    const currentBoundary = feedbackLocation?.image_size
        ? { width: feedbackLocation.image_size.w, height: feedbackLocation.image_size.h }
        : boundary;

    const { rows, cols } = currentBoundary
        ? getGridFromCoarseness(coarsenessPercent, currentBoundary.width, currentBoundary.height)
        : { rows: 1, cols: 1 };

    // --- Original Logic: Mask Building ---
    const buildMask = useCallback(() => {
        const el = imgRef.current;
        if (!el || !el.complete) return;
        const rect = el.getBoundingClientRect();
        const w = Math.round(rect.width);
        const h = Math.round(rect.height);
        if (w <= 0 || h <= 0) return;
        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.drawImage(el, 0, 0, w, h);
        const imageData = ctx.getImageData(0, 0, w, h);
        const data = imageData.data;
        const alpha = new Uint8Array(w * h);
        for (let i = 0; i < alpha.length; i++) {
            alpha[i] = data[i * 4 + 3];
        }
        maskDataRef.current = alpha;
        maskSizeRef.current = { w, h };
    }, []);

    const isPointInsideHand = useCallback((x: number, y: number): boolean => {
        const data = maskDataRef.current;
        const { w, h } = maskSizeRef.current;
        if (!data || w <= 0 || h <= 0) return true;
        const ix = Math.max(0, Math.min(w - 1, Math.floor(x)));
        const iy = Math.max(0, Math.min(h - 1, Math.floor(y)));
        return data[iy * w + ix] >= 128;
    }, []);

    const measureImage = useCallback(() => {
        const el = imgRef.current;
        if (!el) return;
        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
            setBoundary({ width: rect.width, height: rect.height });
            buildMask();
        }
    }, [buildMask]);

    useEffect(() => {
        const el = imgRef.current;
        if (!el) return;
        const ro = new ResizeObserver(() => measureImage());
        ro.observe(el);
        measureImage();
        return () => ro.disconnect();
    }, [measureImage, imageSrc]);

    // --- Original Logic: Coordinate Mapping ---
    const pixelToCell = useCallback((x: number, y: number) => {
        if (!currentBoundary || currentBoundary.width <= 0 || currentBoundary.height <= 0) return null;
        const col = Math.floor((x / currentBoundary.width) * cols);
        const row = Math.floor((y / currentBoundary.height) * rows);
        if (row < 0 || row >= rows || col < 0 || col >= cols) return null;
        return { row, col };
    }, [currentBoundary, rows, cols]);

    const getCellsInBrush = useCallback((centerRow: number, centerCol: number) => {
        const out: Array<{ row: number; col: number }> = [];
        const r0 = Math.max(0, centerRow - brushRadiusCells);
        const r1 = Math.min(rows - 1, centerRow + brushRadiusCells);
        const c0 = Math.max(0, centerCol - brushRadiusCells);
        const c1 = Math.min(cols - 1, centerCol + brushRadiusCells);
        for (let r = r0; r <= r1; r++) {
            for (let c = c0; c <= c1; c++) {
                const dist = Math.sqrt((r - centerRow) ** 2 + (c - centerCol) ** 2);
                if (dist <= brushRadiusCells) out.push({ row: r, col: c });
            }
        }
        return out.length > 0 ? out : [{ row: centerRow, col: centerCol }];
    }, [brushRadiusCells, rows, cols]);

    const handleAction = useCallback((e: React.PointerEvent, erase: boolean) => {
        const el = imgRef.current;
        if (!el || !currentBoundary) return;
        const rect = el.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const cell = pixelToCell(x, y);
        if (!cell) return;

        const key = (r: number, c: number) => `${r},${c}`;
        const set = new Set<string>();
        for (let i = 0; i < chosenPoints.row.length; i++) {
            set.add(key(chosenPoints.row[i], chosenPoints.col[i]));
        }

        const affected = getCellsInBrush(cell.row, cell.col);
        affected.forEach(({ row: r, col: c }) => {
            if (erase) {
                set.delete(key(r, c));
            } else {
                const centerX = ((c + 0.5) / cols) * currentBoundary.width;
                const centerY = ((r + 0.5) / rows) * currentBoundary.height;
                if (isPointInsideHand(centerX, centerY)) set.add(key(r, c));
            }
        });

        const nextPoints: ChosenPointsDict = { row: [], col: [] };
        set.forEach((s) => {
            const [r, c] = s.split(",").map(Number);
            nextPoints.row.push(r);
            nextPoints.col.push(c);
        });

        onUpdate({
            image_path: imageSrc,
            image_size: { w: currentBoundary.width, h: currentBoundary.height },
            segment_size_px: { w: currentBoundary.width / cols, h: currentBoundary.height / rows },
            coarsenessPercent,
            chosenPoints: nextPoints
        });
    }, [currentBoundary, chosenPoints, pixelToCell, isPointInsideHand, getCellsInBrush, rows, cols, imageSrc, coarsenessPercent, onUpdate]);

    const isChosen = useCallback((row: number, col: number) => {
        for (let i = 0; i < chosenPoints.row.length; i++) {
            if (chosenPoints.row[i] === row && chosenPoints.col[i] === col) return true;
        }
        return false;
    }, [chosenPoints]);

    const gridReady = currentBoundary && currentBoundary.width > 0 && currentBoundary.height > 0;

    return (
        <section style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div style={{ padding: "1rem", border: "1px solid #ddd", borderRadius: "8px", background: "#f9f9f9" }}>
                <label style={{ display: "block" }}>Coarseness: {coarsenessPercent}%</label>
                <input type="range" min="0" max="100" step="10" value={coarsenessPercent}
                    onChange={(e) => {
                        onUpdate({
                            image_path: imageSrc,
                            image_size: currentBoundary
                                ? { w: currentBoundary.width, h: currentBoundary.height }
                                : { w: 0, h: 0 },
                            segment_size_px: { w: 0, h: 0 },
                            coarsenessPercent: Number(e.target.value),
                            chosenPoints: { row: [], col: [] }
                        });
                    }}
                />
                <label style={{ display: "block", marginTop: "0.5rem" }}>Brush Size: {brushRadiusCells + 1}</label>
                <input type="range" min="0" max="5" value={brushRadiusCells} onChange={(e) => setBrushRadiusCells(Number(e.target.value))} />

                {/* Touch devices have no right mouse button, so erase needs an
                    explicit mode toggle to be reachable at all. */}
                <button
                    type="button"
                    onClick={() => setEraseMode((v) => !v)}
                    aria-pressed={eraseMode}
                    style={{
                        display: "block",
                        marginTop: "0.75rem",
                        padding: "0.6rem 1rem",
                        minHeight: "44px",
                        fontSize: "1rem",
                        borderRadius: "8px",
                        cursor: "pointer",
                        touchAction: "manipulation",
                        border: eraseMode ? "2px solid #c0392b" : "2px solid #bbb",
                        background: eraseMode ? "#fdecea" : "#fff",
                        color: eraseMode ? "#c0392b" : "#333",
                        fontWeight: eraseMode ? 700 : 400
                    }}
                >
                    {eraseMode ? "Erasing" : "Drawing"}
                </button>
            </div>

            <div style={{ position: "relative", display: "inline-block", userSelect: "none" }}>
                <img
                    ref={imgRef}
                    src={imageSrc}
                    onLoad={measureImage}
                    style={{ display: "block", maxWidth: "100%", height: "auto", pointerEvents: "none", backgroundColor: "white" }}
                />
                {gridReady && (
                    <div
                        style={{
                            position: "absolute", inset: 0,
                            display: "grid",
                            gridTemplateRows: `repeat(${rows}, 1fr)`,
                            gridTemplateColumns: `repeat(${cols}, 1fr)`,
                            cursor: "crosshair",
                            pointerEvents: "auto",
                            // Stop the browser claiming drags as scroll/zoom gestures.
                            // Without this a touch or Pencil stroke pans the page
                            // instead of painting.
                            touchAction: "none",
                            WebkitUserSelect: "none",
                            WebkitTouchCallout: "none"
                        }}
                        onPointerDown={(e) => {
                            // Route all input types (mouse, touch, pen) through one path.
                            e.currentTarget.setPointerCapture(e.pointerId);
                            // Right button, or the Pencil's barrel button, erases;
                            // on touch devices the eraseMode toggle is the only way.
                            const erase = eraseMode || e.button === 2 || e.button === 5;
                            if (erase) { isErasingRef.current = true; handleAction(e, true); }
                            else { isDrawingRef.current = true; handleAction(e, false); }
                        }}
                        onPointerMove={(e) => {
                            const rect = e.currentTarget.getBoundingClientRect();
                            setCursorPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
                            if (isDrawingRef.current) handleAction(e, false);
                            else if (isErasingRef.current) handleAction(e, true);
                        }}
                        onPointerUp={(e) => {
                            if (e.currentTarget.hasPointerCapture(e.pointerId)) {
                                e.currentTarget.releasePointerCapture(e.pointerId);
                            }
                            isDrawingRef.current = false;
                            isErasingRef.current = false;
                        }}
                        onPointerCancel={() => { isDrawingRef.current = false; isErasingRef.current = false; }}
                        onPointerLeave={(e) => {
                            // A captured pen/touch stroke keeps painting outside the
                            // grid; only clear the hover cursor for a real mouse exit.
                            if (e.pointerType === "mouse") {
                                isDrawingRef.current = false;
                                isErasingRef.current = false;
                            }
                            setCursorPos(null);
                        }}
                        onContextMenu={(e) => e.preventDefault()}
                    >
                        {/* Cursor Overlay */}
                        {cursorPos && (
                            <div style={{
                                position: "absolute",
                                left: cursorPos.x - (2 * brushRadiusCells + 1) * (currentBoundary!.width / cols) / 2,
                                top: cursorPos.y - (2 * brushRadiusCells + 1) * (currentBoundary!.height / rows) / 2,
                                width: (2 * brushRadiusCells + 1) * (currentBoundary!.width / cols),
                                height: (2 * brushRadiusCells + 1) * (currentBoundary!.height / rows),
                                borderRadius: "50%",
                                border: "2px solid rgba(0, 100, 200, 0.8)",
                                backgroundColor: "rgba(0, 100, 200, 0.15)",
                                pointerEvents: "none"
                            }} />
                        )}
                        {/* Grid Cells */}
                        {Array.from({ length: rows * cols }).map((_, i) => {
                            const r = Math.floor(i / cols);
                            const c = i % cols;
                            return (
                                <div key={i} style={{
                                    border: "1px solid rgba(0,0,0,0.15)",
                                    backgroundColor: isChosen(r, c) ? "rgba(255, 100, 100, 0.5)" : "transparent",
                                    pointerEvents: "none"
                                }} />
                            );
                        })}
                    </div>
                )}
            </div>
        </section>
    );
};
