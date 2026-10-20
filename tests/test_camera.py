import numpy as np

from cortes_pregacao.vertical.camera import plan_camera
from cortes_pregacao.vertical.detection import Detection, FrameDetections

WIDTH, HEIGHT = 1920, 1080
HALF_WINDOW = HEIGHT * 9 / 16 / 2


def frames_at(*xs: float, cut_at: int | None = None) -> list[FrameDetections]:
    return [
        FrameDetections(i == cut_at, (Detection(x, 80, "face", 300.0),)) for i, x in enumerate(xs)
    ]


def test_window_stays_inside_frame() -> None:
    camera = plan_camera(frames_at(*[50.0] * 120), WIDTH, HEIGHT)

    assert camera.centres.min() >= HALF_WINDOW - 1e-6


def test_small_moves_inside_dead_zone_are_ignored() -> None:
    jitter = [960 + 20 * np.sin(i / 3) for i in range(200)]

    camera = plan_camera(frames_at(*jitter), WIDTH, HEIGHT)

    assert np.ptp(camera.centres) < 5


def test_follows_a_walk_smoothly() -> None:
    walk = [600.0] * 60 + list(np.linspace(600, 1300, 120)) + [1300.0] * 240

    camera = plan_camera(frames_at(*walk), WIDTH, HEIGHT)

    assert abs(camera.centres[-1] - 1300) < 60
    assert np.abs(np.diff(camera.centres)).max() < 8  # no jumps


def test_jumps_at_forced_cut_instead_of_sliding() -> None:
    xs = [600.0] * 100 + [1300.0] * 100

    camera = plan_camera(frames_at(*xs), WIDTH, HEIGHT, forced_cuts=[100])

    assert abs(camera.centres[100] - 1300) < 1
    assert camera.scene_cuts == [100]


def test_audience_heads_are_ignored() -> None:
    frames = [
        FrameDetections(
            False, (Detection(1500, 200, "face", 900.0), Detection(700, 60, "face", 300.0))
        )
    ] * 50

    camera = plan_camera(frames, WIDTH, HEIGHT)

    assert abs(camera.subject[0] - 700) < 1


def test_target_picks_person_by_position() -> None:
    frames = [
        FrameDetections(
            False, (Detection(400, 90, "face", 300.0), Detection(1500, 60, "face", 300.0))
        )
    ] * 50

    assert abs(plan_camera(frames, WIDTH, HEIGHT).subject[0] - 400) < 1
    assert abs(plan_camera(frames, WIDTH, HEIGHT, target=0.8).subject[0] - 1500) < 1
