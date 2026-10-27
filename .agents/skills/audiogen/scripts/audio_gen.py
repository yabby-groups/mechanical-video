#!/usr/bin/env python3
"""Generate MP3 speech using an OpenAI-compatible audio endpoint."""

import argparse
import asyncio
import inspect
import os
import sys
from pathlib import Path
from typing import Any


async def read_audio_bytes(response: Any) -> bytes:
    if isinstance(response, bytes):
        return response
    if hasattr(response, "read"):
        data = response.read()
        if inspect.isawaitable(data):
            data = await data
        if isinstance(data, bytes):
            return data
    content = getattr(response, "content", None)
    return content if isinstance(content, bytes) else b""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    text = parser.add_mutually_exclusive_group(required=True)
    text.add_argument("--text", help="Exact text to speak")
    text.add_argument("--text-file", type=Path, help="UTF-8 file containing speech text")
    parser.add_argument("--model", default="qwen3-tts-flash")
    parser.add_argument("--voice", default="Roy")
    parser.add_argument("--out", type=Path, default=Path("output.mp3"))
    args = parser.parse_args()
    try:
        args.text = args.text_file.read_text(encoding="utf-8") if args.text_file else args.text
    except (OSError, UnicodeError):
        parser.error("Cannot read --text-file as UTF-8")
    if not args.text.strip():
        parser.error("Speech text must not be empty")
    return args


async def generate(args: argparse.Namespace) -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY before generating audio")
    try:
        from openai import APIStatusError, AsyncOpenAI
    except ImportError:
        raise RuntimeError("Install openai into the Python environment used to run this script") from None
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or "https://huabot.com/v1"
    async with AsyncOpenAI(api_key=api_key, base_url=base_url, max_retries=0) as client:
        try:
            response = await client.audio.speech.create(
                model=args.model, voice=args.voice, input=args.text, response_format="mp3"
            )
            audio = await read_audio_bytes(response)
        except APIStatusError as error:
            raise RuntimeError(f"Audio provider request failed: HTTP {error.status_code}") from None
        except Exception:
            raise RuntimeError("Audio provider request or response read failed; check endpoint and connectivity") from None
    if not audio:
        raise RuntimeError("Audio provider returned no audio data")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(audio)
    print(f"Audio saved to {args.out.resolve()}")


def main() -> int:
    args = parse_args()
    try:
        asyncio.run(generate(args))
    except (RuntimeError, OSError) as error:
        # Provider response bodies and request inputs can contain private data.
        message = str(error) if isinstance(error, RuntimeError) else "Cannot save audio output"
        print(f"Error: {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
