---
name: audiogen
description: Generate spoken audio from text using an OpenAI-compatible speech API. Use for narration, voiceovers, and reading text aloud; not music generation, voice cloning, or transcription.
---

# Audio Generation

Generate MP3 speech with the bundled `scripts/audio_gen.py`; do not recreate an SDK runner.

## Inputs and workflow

- Preserve supplied speech text verbatim. If asked to write narration, compose it according to the brief before synthesis; do not read the task instructions aloud.
- Default to model `qwen3-tts-flash`, voice `Roy`, and MP3. Honor explicitly requested model and voice; do not silently switch them after a failure.
- Use `OPENAI_API_KEY` and optional `OPENAI_BASE_URL` (default `https://huabot.com/v1`) from the runtime environment. Never print or save credentials. Skill2API forwards request environment values with worker-level fallbacks.
- Use a Python interpreter that has the `openai` package installed. If a virtual environment is configured, verify its interpreter and import; a set `VIRTUAL_ENV` alone does not establish that `python3` uses it. If missing, install `openai` into the selected environment using its package manager, or report the dependency limitation.
- Resolve the script relative to this skill package, not the task directory. In Skill2API Docker mode it is `/skill2api/skills/audiogen/scripts/audio_gen.py`.
- Save final audio inside the current task output directory. Default to `output.mp3`; honor requested filenames and avoid replacing existing deliverables unless requested.

```bash
python3 /skill2api/skills/audiogen/scripts/audio_gen.py \
  --text '你好，这是语音生成测试。' --out ./output.mp3
```

Use `--text-file <utf8-file>` instead of `--text` for longer text. The two inputs are mutually exclusive. Optional `--model` and `--voice` override defaults. The script disables automatic SDK retries to avoid duplicating uncertain submissions.

## Verification and delivery

Check that the saved file is non-empty. When `ffprobe` is available, verify it is decodable audio with positive duration. Report the actual saved path after success; never claim success for an empty or failed response. On failure, report the actionable error without exposing keys or raw provider response bodies. Do not automatically resubmit an uncertain provider request.
