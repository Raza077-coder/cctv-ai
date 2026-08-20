"""Crowd density analytics: count, level, per-zone counts, simple heatmap."""
from __future__ import annotations

import cv2
import numpy as np


def crowd_level(count: int) -> str:
    if count == 0:
        return "empty"
    if count < 3:
        return "low"
    if count < 8:
        return "moderate"
    if count < 15:
        return "high"
    return "critical"


def draw_heatmap(frame, centers: list[tuple[float, float]], radius: int = 60) -> np.ndarray:
    """Render a simple Gaussian heat overlay on top of the frame."""
    h, w = frame.shape[:2]
    heat = np.zeros((h, w), dtype=np.float32)
    for (cx, cy) in centers:
        try:
            cv2.circle(heat, (int(cx), int(cy)), radius, 1.0, -1)
        except Exception:
            continue
    heat = cv2.GaussianBlur(heat, (0, 0), sigmaX=radius / 2.5)
    heat = (heat / (np.max(heat) + 1e-9) * 255).astype(np.uint8)
    heatmap_bgr = cv2.applyColorMap(heat, cv2.COLORMAP_JET)
    return cv2.addWeighted(frame, 0.65, heatmap_bgr, 0.35, 0)


def zone_counts(people: list[tuple[float, float]], grid: tuple[int, int] = (4, 3)) -> list[dict]:
    """Bucket people positions into an exclusive grid; returns per-cell counts."""
    if not people:
        return []
    xs = [p[0] for p in people]
    ys = [p[1] for p in people]
    max_x, max_y = max(xs), max(ys)
    if max_x <= 0 or max_y <= 0:
        return []
    cell_w = max_x / grid[0]
    cell_h = max_y / grid[1]
    counts: list[dict] = []
    for gy in range(grid[1]):
        for gx in range(grid[0]):
            # exclusive upper bound, except the last row/column (inclusive edge)
            x_hi = (gx + 1) * cell_w if gx < grid[0] - 1 else max_x + 1e-9
            y_hi = (gy + 1) * cell_h if gy < grid[1] - 1 else max_y + 1e-9
            count = sum(
                1 for (px, py) in people
                if (gx * cell_w <= px < x_hi) and (gy * cell_h <= py < y_hi)
            )
            counts.append({"cell": f"{gx}x{gy}", "count": count})
    return counts
