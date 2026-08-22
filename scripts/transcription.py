"""Optional local Whisper transcription."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json


@dataclass
class Segment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    text: str
    segments: list[Segment]
    language: str | None
    backend: str


def transcribe_faster_whisper(
    audio_path: str,
    *,
    model_name: str = "small",
    device: str = "auto",
    compute_type: str = "auto",
) -> TranscriptResult:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "tool_missing:faster-whisper; install with "
            "`python -m pip install faster-whisper`"
        ) from exc

    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
    )
    segments_iter, info = model.transcribe(
        audio_path,
        vad_filter=True,
    )
    segments: list[Segment] = []
    texts: list[str] = []
    for s in segments_iter:
        text = (s.text or "").strip()
        if not text:
            continue
        segments.append(Segment(float(s.start), float(s.end), text))
        texts.append(text)

    return TranscriptResult(
        text="\n".join(texts),
        segments=segments,
        language=getattr(info, "language", None),
        backend="faster-whisper",
    )


def save_transcript(result: TranscriptResult, output_dir: str) -> tuple[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    txt = out / "transcript.txt"
    js = out / "transcript.json"

    txt.write_text(result.text, encoding="utf-8")
    js.write_text(
        json.dumps(
            {
                "text": result.text,
                "language": result.language,
                "backend": result.backend,
                "segments": [asdict(s) for s in result.segments],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return str(txt), str(js)
