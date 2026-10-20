"""Command-line interface: ``cortes <command>``."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from cortes_pregacao.asr.local import LocalTranscriber
from cortes_pregacao.asr.remote import RemoteHost, RemoteTranscriber
from cortes_pregacao.media import extract_speech_audio
from cortes_pregacao.transcript import Transcript


def _transcribe(args: argparse.Namespace) -> None:
    if args.job:
        if not args.host:
            raise SystemExit("--job exige --host")
        RemoteTranscriber(RemoteHost(args.host), model=args.model).wait_and_fetch(
            args.job, args.output
        )
    else:
        transcriber = (
            RemoteTranscriber(RemoteHost(args.host), model=args.model)
            if args.host
            else LocalTranscriber(model=args.model)
        )
        with tempfile.TemporaryDirectory() as tmp:
            audio = extract_speech_audio(args.video, Path(tmp) / "audio.wav")
            transcriber.transcribe(audio, args.output)
    transcript = Transcript.load(args.output)
    print(f"{len(transcript.words)} palavras -> {args.output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cortes", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    transcribe = commands.add_parser(
        "transcribe", help="transcreve o vídeo com tempo por palavra (WhisperX)"
    )
    transcribe.add_argument("video", type=Path)
    transcribe.add_argument("-o", "--output", type=Path, required=True)
    transcribe.add_argument(
        "--host", help="host SSH com GPU; sem ele, roda nesta máquina (ex.: no próprio leitao)"
    )
    transcribe.add_argument("--model", default="large-v3")
    transcribe.add_argument("--job", help="retoma um job remoto já iniciado, pelo id")
    transcribe.set_defaults(handler=_transcribe)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    main()
