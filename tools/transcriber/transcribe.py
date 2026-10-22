"""Транскрибация аудио через OpenAI-совместимый API (OpenAI, Groq и т.п.).

Настройка через переменные окружения:
    OPENAI_API_KEY         — ключ API (обязательно)
    OPENAI_BASE_URL        — другой провайдер, напр. https://api.groq.com/openai/v1
    TRANSCRIBE_MODEL       — модель (по умолчанию gpt-4o-mini-transcribe)

Использование:
    python transcribe.py "Voice.m4a" [-l ru] [-o out.txt]

    from transcribe import transcribe
    text = transcribe("Voice.m4a", language="ru")
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from openai import OpenAI

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # лимит API на один файл
CHUNK_SECONDS = 10 * 60              # длина куска при нарезке длинных записей
DEFAULT_MODEL = os.getenv("TRANSCRIBE_MODEL", "gpt-4o-mini-transcribe")


def _split_audio(path: Path, workdir: Path) -> list[Path]:
    """Режет файл на куски по CHUNK_SECONDS (mono 16 kHz mp3) через ffmpeg."""
    pattern = workdir / "chunk_%03d.mp3"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "16000",
         "-b:a", "64k", "-f", "segment", "-segment_time", str(CHUNK_SECONDS),
         str(pattern)],
        check=True,
    )
    return sorted(workdir.glob("chunk_*.mp3"))


def _transcribe_file(client: OpenAI, path: Path, model: str,
                     language: str | None, prompt: str | None) -> str:
    kwargs = {"model": model, "response_format": "text"}
    if language:
        kwargs["language"] = language
    if prompt:
        kwargs["prompt"] = prompt
    with path.open("rb") as f:
        result = client.audio.transcriptions.create(file=f, **kwargs)
    return (result if isinstance(result, str) else result.text).strip()


def transcribe(path: str | Path, language: str | None = None,
               model: str = DEFAULT_MODEL, prompt: str | None = None,
               client: OpenAI | None = None) -> str:
    """Возвращает текст аудиофайла. Файлы >25 МБ режутся на куски автоматически."""
    path = Path(path)
    client = client or OpenAI()

    if path.stat().st_size <= MAX_UPLOAD_BYTES:
        return _transcribe_file(client, path, model, language, prompt)

    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for chunk in _split_audio(path, Path(tmp)):
            # хвост предыдущего куска как подсказка — меньше разрывов на стыках
            hint = parts[-1][-200:] if parts else prompt
            parts.append(_transcribe_file(client, chunk, model, language, hint))
        return "\n".join(parts)


def main() -> None:
    p = argparse.ArgumentParser(description="Транскрибация аудио через API")
    p.add_argument("file")
    p.add_argument("-l", "--language", help="код языка, напр. ru (ускоряет и уточняет)")
    p.add_argument("-m", "--model", default=DEFAULT_MODEL)
    p.add_argument("-o", "--output", help="куда сохранить текст (по умолчанию stdout)")
    args = p.parse_args()

    text = transcribe(args.file, language=args.language, model=args.model)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # понятное сообщение вместо трейсбэка
        sys.exit(f"Ошибка: {e}")
