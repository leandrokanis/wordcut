"""Virtual camera operator: where the 9:16 window sits in each frame.

Follows one person by continuity, then smooths like a human operator: median
and Savitzky-Golay filtering, a dead zone (small moves are ignored) and limited
speed/acceleration. At scene cuts the window jumps instead of sliding.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import pairwise

import numpy as np
import numpy.typing as npt
from scipy.signal import medfilt, savgol_filter

from cortes_pregacao.vertical.detection import Detection, FrameDetections

ASPECT = 9 / 16
HEADS_REGION = 0.42  # heads must be in the top 42% of the frame (ignores the audience)
MATCH_RADIUS_PX = 120
MATCH_RADIUS_GROWTH_PX = 20  # per frame without a match

MEDIAN_FRAMES = 15
SMOOTH_FRAMES = 91
FINAL_SMOOTH_FRAMES = 31

Path1D = npt.NDArray[np.float64]


@dataclass(frozen=True)
class OperatorStyle:
    dead_zone_px: float = 45.0
    max_speed_px: float = 6.0  # per frame, source pixels
    max_accel_px: float = 0.18
    gain: float = 0.10


DEFAULT_STYLE = OperatorStyle()


@dataclass(frozen=True)
class CameraPath:
    centres: Path1D  # window centre x per frame, source pixels
    subject: Path1D  # tracked person x per frame
    scene_cuts: list[int] = field(default_factory=list)

    def max_offset(self) -> float:
        return float(np.abs(self.subject - self.centres).max())


def plan_camera(
    frames: Sequence[FrameDetections],
    width: int,
    height: int,
    target: float | None = None,
    forced_cuts: Sequence[int] = (),
    style: OperatorStyle = DEFAULT_STYLE,
) -> CameraPath:
    """``target``: horizontal position (0-1) of who to follow; default is the largest face.

    ``forced_cuts``: frame indexes where the shot changes for editorial reasons
    (e.g. a jump between edit-list segments).
    """
    cuts = sorted({i for i, f in enumerate(frames) if f.scene_cut} | set(forced_cuts))
    subject = track_subject(frames, height, width, target, set(cuts))
    window = height * ASPECT
    centres = np.empty_like(subject)
    for start, end in pairwise([0, *cuts, len(subject)]):
        if end > start:
            centres[start:end] = _operate(subject[start:end], style)
    centres = np.clip(centres, window / 2, width - window / 2)
    return CameraPath(centres, subject, cuts)


def track_subject(
    frames: Sequence[FrameDetections],
    height: int,
    width: int,
    target: float | None,
    cuts: set[int],
) -> Path1D:
    positions: list[float | None] = []
    current: float | None = None
    misses = 0
    for index, frame in enumerate(frames):
        heads = [p for p in frame.people if p.head_y < height * HEADS_REGION]
        if index in cuts:
            current, misses = None, 0
        if not heads:
            misses += 1  # keep the last known position
        elif current is None:
            current = _pick(heads, width, target)
        else:
            matched = _follow(heads, current, MATCH_RADIUS_PX + MATCH_RADIUS_GROWTH_PX * misses)
            current, misses = (matched, 0) if matched is not None else (current, misses + 1)
        positions.append(current)
    first = next((p for p in positions if p is not None), width / 2)
    return np.array([first if p is None else p for p in positions], dtype=np.float64)


def _pick(heads: list[Detection], width: int, target: float | None) -> float:
    if target is None:
        return max(heads, key=lambda p: p.size).x
    return min(heads, key=lambda p: abs(p.x - target * width)).x


def _follow(heads: list[Detection], current: float, radius: float) -> float | None:
    """Position of the same person in this frame: the nearest head, if close enough."""
    nearest = min(heads, key=lambda p: abs(p.x - current))
    return nearest.x if abs(nearest.x - current) < radius else None


def _operate(subject: Path1D, style: OperatorStyle) -> Path1D:
    smoothed = subject
    if len(smoothed) >= MEDIAN_FRAMES:
        smoothed = medfilt(smoothed, MEDIAN_FRAMES)
    if len(smoothed) >= SMOOTH_FRAMES:
        smoothed = savgol_filter(smoothed, SMOOTH_FRAMES, 2)

    path = np.empty_like(smoothed)
    position, speed = float(smoothed[0]), 0.0
    for index, wanted in enumerate(smoothed):
        error = wanted - position
        if abs(error) <= style.dead_zone_px:
            desired = 0.0
        else:
            desired = np.sign(error) * min(
                style.max_speed_px, (abs(error) - style.dead_zone_px) * style.gain
            )
        speed += float(np.clip(desired - speed, -style.max_accel_px, style.max_accel_px))
        position += speed
        path[index] = position
    if len(path) >= FINAL_SMOOTH_FRAMES:
        path = savgol_filter(path, FINAL_SMOOTH_FRAMES, 2)
    return path
