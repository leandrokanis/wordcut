"""Command-line interface: ``cortes <command>``."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from cortes_pregacao.asr import Transcriber
from cortes_pregacao.asr.local import LocalTranscriber
from cortes_pregacao.asr.remote import RemoteHost, RemoteTranscriber
from cortes_pregacao.media import extract_speech_audio
from cortes_pregacao.overview import overview_lines, word_lines
from cortes_pregacao.sermon import cut_sermon, transcribe_live
from cortes_pregacao.sermon_folder import SermonFolder, default_root, folder_name
from cortes_pregacao.timefmt import format_timestamp, parse_timestamp
from cortes_pregacao.transcript import Transcript
from cortes_pregacao.youtube import YouTube


def _make_transcriber(args: argparse.Namespace) -> Transcriber:
    if args.host:
        return RemoteTranscriber(RemoteHost(args.host), model=args.model)
    return LocalTranscriber(model=args.model)


def _info(args: argparse.Namespace) -> None:
    info = YouTube().info(args.url)
    print(
        json.dumps(
            {
                "titulo": info.title,
                "data_culto": info.service_date.isoformat(),
                "duracao": format_timestamp(info.duration),
                "status": info.live_status,
                "terminada": info.is_finished,
                "pasta_sugerida": str(default_root() / folder_name(info.service_date, "Pregação")),
            },
            ensure_ascii=False,
            indent=1,
        )
    )


def _transcribe(args: argparse.Namespace) -> None:
    if args.job:
        if not args.host:
            raise SystemExit("--job exige --host")
        RemoteTranscriber(RemoteHost(args.host), model=args.model).wait_and_fetch(
            args.job, args.output
        )
    else:
        with tempfile.TemporaryDirectory() as tmp:
            audio = extract_speech_audio(args.video, Path(tmp) / "audio.wav")
            _make_transcriber(args).transcribe(audio, args.output)
    print(f"{len(Transcript.load(args.output).words)} palavras -> {args.output}")


def _transcribe_live(args: argparse.Namespace) -> None:
    folder = SermonFolder(args.dir)
    transcript = transcribe_live(
        YouTube(), _make_transcriber(args), args.url, folder, args.start, args.end
    )
    print(f"{len(transcript.words)} palavras -> {folder.live_words}")


def _overview(args: argparse.Namespace) -> None:
    transcript = Transcript.load(args.transcript)
    render = word_lines if args.words else overview_lines
    for line in render(transcript, args.start or 0.0, args.end or float("inf")):
        print(line)


def _cut(args: argparse.Namespace) -> None:
    folder = SermonFolder(args.dir)
    result = cut_sermon(YouTube(), args.url, folder, args.first_word, args.last_word)
    print(
        f"pregação: {format_timestamp(result.live_start)} -> {format_timestamp(result.live_end)}"
        f" na live ({format_timestamp(result.duration)})\n"
        f"desvio do download: {result.section_offset_error:+.3f} s\n"
        f"{folder.sermon_video}\n{folder.words} ({result.words} palavras)"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cortes", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    info = commands.add_parser("info", help="título, data do culto e duração da live")
    info.add_argument("url")
    info.set_defaults(handler=_info)

    transcribe = commands.add_parser("transcribe", help="transcreve um arquivo de mídia")
    transcribe.add_argument("video", type=Path)
    transcribe.add_argument("-o", "--output", type=Path, required=True)
    transcribe.add_argument("--job", help="retoma um job remoto já iniciado, pelo id")
    _add_asr_options(transcribe)
    transcribe.set_defaults(handler=_transcribe)

    live = commands.add_parser(
        "transcribe-live", help="baixa o áudio da live e transcreve (inteira ou uma faixa)"
    )
    live.add_argument("url")
    live.add_argument("--dir", type=Path, required=True, help="pasta da pregação")
    live.add_argument("--start", type=parse_timestamp, help="início aproximado da pregação")
    live.add_argument("--end", type=parse_timestamp, help="fim aproximado da pregação")
    _add_asr_options(live)
    live.set_defaults(handler=_transcribe_live)

    overview = commands.add_parser("overview", help="transcrição legível, uma frase por linha")
    overview.add_argument("transcript", type=Path)
    overview.add_argument("--start", type=parse_timestamp)
    overview.add_argument("--end", type=parse_timestamp)
    overview.add_argument(
        "--words", action="store_true", help="uma palavra por linha (início, fim)"
    )
    overview.set_defaults(handler=_overview)

    cut = commands.add_parser("cut", help="corta a pregação com fades e gera palavras.json")
    cut.add_argument("url")
    cut.add_argument("--dir", type=Path, required=True, help="pasta da pregação")
    cut.add_argument("--first-word", type=parse_timestamp, required=True, help="tempo na live")
    cut.add_argument("--last-word", type=parse_timestamp, required=True, help="fim, na live")
    cut.set_defaults(handler=_cut)
    return parser


def _add_asr_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--host", help="host SSH com GPU; sem ele, roda nesta máquina (ex.: no próprio leitao)"
    )
    parser.add_argument("--model", default="large-v3")


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    main()
