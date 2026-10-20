"""Command-line interface: ``cortes <command>``."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from cortes_pregacao.asr.remote import RemoteHost, RemoteTranscriber
from cortes_pregacao.media import extract_speech_audio
from cortes_pregacao.transcript import Transcript

DEFAULT_HOST = "leitao"


def _transcribe(args: argparse.Namespace) -> None:
    transcriber = RemoteTranscriber(RemoteHost(args.host), model=args.model)
    if args.job:
        transcriber.wait_and_fetch(args.job, args.output)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            audio = extract_speech_audio(args.video, Path(tmp) / "audio.wav")
            transcriber.transcribe(audio, args.output)
    transcript = Transcript.load(args.output)
    print(f"{len(transcript.words)} palavras -> {args.output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cortes", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    transcribe = commands.add_parser(
        "transcribe", help="transcreve o vídeo com tempo por palavra (WhisperX no host remoto)"
    )
    transcribe.add_argument("video", type=Path)
    transcribe.add_argument("-o", "--output", type=Path, required=True)
    transcribe.add_argument("--host", default=DEFAULT_HOST, help="host SSH com GPU")
    transcribe.add_argument("--model", default="large-v3")
    transcribe.add_argument("--job", help="retoma um job remoto já iniciado, pelo id")
    transcribe.set_defaults(handler=_transcribe)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    main()
