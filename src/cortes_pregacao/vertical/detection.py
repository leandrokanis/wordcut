"""Per-frame people detection and scene-cut detection (OpenCV)."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from cv2.typing import MatLike

SCENE_CUT_DISTANCE = 0.35  # Bhattacharyya distance between HSV histograms
FACE_SEARCH_WIDTH = 960  # faces are searched on a downscaled frame; the preacher stays large
DETECTION_STRIDE = 3  # detect people every 3rd frame; the camera smooths over ~3 s anyway
HOG_WIDTH = 640
MIN_FACE_PX = 20

Frame = MatLike


@dataclass(frozen=True)
class Detection:
    x: float  # horizontal centre, source pixels
    size: int  # face width or body height
    kind: str  # "face" | "body"
    head_y: float


@dataclass(frozen=True)
class FrameDetections:
    scene_cut: bool
    people: tuple[Detection, ...]


class PeopleDetector:
    """Faces (Haar frontal + profile, both directions); HOG bodies when no face is found."""

    def __init__(self) -> None:
        cascades = Path(cv2.data.haarcascades)  # type: ignore[attr-defined]  # missing from stubs
        self._frontal = cv2.CascadeClassifier(str(cascades / "haarcascade_frontalface_default.xml"))
        self._profile = cv2.CascadeClassifier(str(cascades / "haarcascade_profileface.xml"))
        self._hog = cv2.HOGDescriptor()
        people = np.asarray(cv2.HOGDescriptor.getDefaultPeopleDetector(), dtype=np.float32)
        self._hog.setSVMDetector(people)

    def detect(self, frame: Frame) -> tuple[Detection, ...]:
        scale = min(1.0, FACE_SEARCH_WIDTH / frame.shape[1])
        gray = cv2.cvtColor(cv2.resize(frame, None, fx=scale, fy=scale), cv2.COLOR_BGR2GRAY)
        faces = tuple(_rescale(face, scale) for face in self._faces(gray))
        return faces if faces else self._bodies(frame)

    def _faces(self, gray: Frame) -> tuple[Detection, ...]:
        width = gray.shape[1]
        found = [
            Detection(x + w / 2, int(w), "face", y + h / 2)
            for cascade in (self._frontal, self._profile)
            for x, y, w, h in cascade.detectMultiScale(gray, 1.1, 5, minSize=(MIN_FACE_PX,) * 2)
        ]
        mirrored = self._profile.detectMultiScale(
            cv2.flip(gray, 1), 1.1, 5, minSize=(MIN_FACE_PX,) * 2
        )
        found += [
            Detection(width - (x + w / 2), int(w), "face", y + h / 2) for x, y, w, h in mirrored
        ]
        return tuple(found)

    def _bodies(self, frame: Frame) -> tuple[Detection, ...]:
        scale = HOG_WIDTH / frame.shape[1]
        small = cv2.resize(frame, None, fx=scale, fy=scale)
        rects, _ = self._hog.detectMultiScale(small, winStride=(8, 8))
        return tuple(
            Detection((x + w / 2) / scale, int(h / scale), "body", (y + h * 0.15) / scale)
            for x, y, w, h in rects
        )


def _rescale(detection: Detection, scale: float) -> Detection:
    return Detection(
        detection.x / scale, round(detection.size / scale), detection.kind, detection.head_y / scale
    )


class SceneCutDetector:
    def __init__(self) -> None:
        self._previous: Frame | None = None

    def is_cut(self, frame: Frame) -> bool:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        histogram = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
        cv2.normalize(histogram, histogram)
        previous, self._previous = self._previous, histogram
        if previous is None:
            return False
        distance = cv2.compareHist(previous, histogram, cv2.HISTCMP_BHATTACHARYYA)
        return bool(distance > SCENE_CUT_DISTANCE)


Progress = Callable[[int, int], None]
"""Called with (frames done, total frames)."""


def detect_frames(
    video: Path,
    cache: Path | None = None,
    stride: int = DETECTION_STRIDE,
    progress: Progress | None = None,
) -> list[FrameDetections]:
    """Detections for every frame of ``video``; cached as JSON when ``cache`` is given.

    People are detected every ``stride`` frames and on every scene cut; frames
    in between reuse the last detection. Scene cuts are checked on every frame.
    """
    if cache and cache.exists():
        return _load(cache)
    people, scenes = PeopleDetector(), SceneCutDetector()
    capture = cv2.VideoCapture(str(video))
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    frames: list[FrameDetections] = []
    last: tuple[Detection, ...] = ()
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        cut = scenes.is_cut(frame)
        if cut or len(frames) % stride == 0:
            last = people.detect(frame)
        frames.append(FrameDetections(cut, last))
        if progress:
            progress(len(frames), total)
    capture.release()
    if cache:
        cache.write_text(json.dumps([asdict(f) for f in frames]), encoding="utf-8")
    return frames


def _load(cache: Path) -> list[FrameDetections]:
    data: list[dict[str, Any]] = json.loads(cache.read_text(encoding="utf-8"))
    return [
        FrameDetections(item["scene_cut"], tuple(Detection(**p) for p in item["people"]))
        for item in data
    ]
