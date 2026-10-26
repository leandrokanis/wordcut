from pathlib import Path

import cv2
import numpy as np
import pytest

from wordcut.vertical import detection
from wordcut.vertical.detection import Detection, _rescale, detect_frames


def blank_video(path: Path, frames: int, cut_at: int | None = None) -> Path:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter.fourcc(*"MJPG"), 30, (64, 48))
    for index in range(frames):
        # blue, then red after the cut (black/white share the same hue histogram)
        bgr = (0, 0, 255) if cut_at is not None and index >= cut_at else (255, 0, 0)
        writer.write(np.full((48, 64, 3), bgr, dtype=np.uint8))
    writer.release()
    return path


def test_rescale_maps_back_to_source_pixels() -> None:
    face = _rescale(Detection(100.0, 40, "face", 50.0), scale=0.5)

    assert face == Detection(200.0, 80, "face", 100.0)


def test_people_detected_every_stride_frames_and_on_cuts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def fake_detect(self: object, frame: object) -> tuple[Detection, ...]:
        calls.append(len(calls))
        return (Detection(float(len(calls)), 10, "face", 1.0),)

    monkeypatch.setattr(detection.PeopleDetector, "detect", fake_detect)
    video = blank_video(tmp_path / "v.avi", frames=10, cut_at=5)

    frames = detect_frames(video, stride=3)

    assert len(frames) == 10
    assert len(calls) == 5  # frames 0, 3, 5 (cut), 6, 9
    assert frames[1].people == frames[0].people  # reused between detections
    assert frames[5].scene_cut
