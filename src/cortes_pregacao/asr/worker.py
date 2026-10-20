"""WhisperX transcription worker, meant to run on a CUDA host.

Usage: python -m cortes_pregacao.asr.worker AUDIO OUTPUT_JSON [--model NAME]
"""

from __future__ import annotations

import argparse
import gc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cortes_pregacao.asr.prompt_echo import remove_prompt_echoes
from cortes_pregacao.transcript import RawWord, Transcript, fill_missing_times

LANGUAGE = "pt"
SAMPLE_RATE = 16_000

# Whisper tends to drop disfluencies. Priming the decoder with them makes it
# transcribe hesitations verbatim, so the editor can find and cut them.
HESITATION_PROMPT = "Hã, é... então, né, tipo assim, é, o, o Senhor, ãh, a gente, hum, aí, né."


@dataclass(frozen=True)
class WorkerConfig:
    model: str = "large-v3"
    device: str = "cuda"
    compute_type: str = "int8_float16"
    batch_size: int = 8


def transcribe(audio_path: Path, config: WorkerConfig) -> Transcript:
    import whisperx

    audio = whisperx.load_audio(str(audio_path))
    segments = _recognize(whisperx, audio, config)
    raw_words = remove_prompt_echoes(_align(whisperx, audio, segments, config), HESITATION_PROMPT)
    words = fill_missing_times(raw_words, total_duration=len(audio) / SAMPLE_RATE)
    return Transcript(
        words=tuple(words),
        language=LANGUAGE,
        model=f"whisperx/{config.model}",
        metadata={"initial_prompt": HESITATION_PROMPT},
    )


def _recognize(whisperx: Any, audio: Any, config: WorkerConfig) -> list[dict[str, Any]]:
    model = whisperx.load_model(
        config.model,
        config.device,
        compute_type=config.compute_type,
        language=LANGUAGE,
        asr_options={"initial_prompt": HESITATION_PROMPT, "suppress_numerals": True},
    )
    print("etapa 1/2: reconhecimento", flush=True)
    result = model.transcribe(
        audio, batch_size=config.batch_size, language=LANGUAGE, print_progress=True
    )
    del model
    _release_gpu_memory()  # recognition and alignment don't fit in 6 GB together
    segments: list[dict[str, Any]] = result["segments"]
    return segments


def _align(
    whisperx: Any, audio: Any, segments: list[dict[str, Any]], config: WorkerConfig
) -> list[RawWord]:
    print("etapa 2/2: alinhamento por palavra", flush=True)
    align_model, align_metadata = whisperx.load_align_model(
        language_code=LANGUAGE, device=config.device
    )
    aligned = whisperx.align(
        segments,
        align_model,
        align_metadata,
        audio,
        config.device,
        return_char_alignments=False,
        print_progress=True,
    )
    return [
        RawWord(
            text=item["word"].strip(),
            start=item.get("start"),
            end=item.get("end"),
            score=item.get("score"),
        )
        for item in aligned["word_segments"]
        if item["word"].strip()
    ]


def _release_gpu_memory() -> None:
    import torch

    gc.collect()
    torch.cuda.empty_cache()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", default=WorkerConfig.model)
    args = parser.parse_args()

    transcript = transcribe(args.audio, WorkerConfig(model=args.model))
    transcript.save(args.output)
    estimated = sum(word.estimated for word in transcript.words)
    print(f"{len(transcript.words)} palavras ({estimated} com tempo estimado) -> {args.output}")


if __name__ == "__main__":
    main()
