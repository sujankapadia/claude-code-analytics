# Demo Video Pipeline

Automated narrated demo video generation — fully scripted, no screen recording or manual voiceover needed.

## Pipeline Architecture

```
Script (JSON) → Piper TTS (WAV clips) → Playwright (browser video) → ffmpeg (final MP4)
```

1. A **demo script** (`active-sessions-script.json`) defines segments with narration text and browser actions
2. **Piper TTS** generates a WAV audio clip for each segment's narration
3. **Playwright** launches a browser with `recordVideo`, executes each action, and sleeps for the duration of the corresponding audio clip so video and narration stay in sync
4. **ffmpeg** concatenates audio clips (with silence gaps for pauses) and merges the combined audio track with the browser video into a final MP4

## Prerequisites

```bash
# Python dependencies
pip install piper-tts pathvalidate playwright

# Browser binary for Playwright
playwright install chromium

# ffmpeg (brew install ffmpeg) — provides both ffmpeg and ffprobe
```

### Download the TTS voice model

Piper requires a local ONNX model file. Download it once:

```bash
python -m piper.download_voices --download-dir demo/models en_US-lessac-medium
```

This creates `demo/models/en_US-lessac-medium.onnx` (~60 MB). The models directory is gitignored.

## Usage

1. Start the API and frontend dev servers:
   ```bash
   claude-code-api                  # port 8000
   cd frontend && npm run dev       # port 5173
   ```

2. Make sure you have at least one active Claude Code session running (the demo clicks a session card).

3. Run the pipeline:
   ```bash
   python demo/run_demo.py
   ```

4. Output lands in `demo/output/active-sessions-demo.mp4`.

## How it works

### Phase A: Audio generation
For each segment, the narration text is piped to `piper --model <model.onnx> --output_file segment_N.wav`. Clip durations are measured with `ffprobe` to calculate Playwright timing.

### Phase B: Browser recording
Playwright launches Chromium with `record_video_dir` and executes each segment's action (navigate, click, scroll, or wait). After each action, it sleeps for `max(audio_duration, pause_after_ms)` so the video has enough footage to cover the narration.

### Phase C: Audio/video merge
Audio clips are concatenated with silence gaps using ffmpeg's concat demuxer. The combined audio is merged with the browser video: `ffmpeg -i video.webm -i combined_audio.wav -c:v libx264 -c:a aac -shortest output.mp4`.

## Customizing the script

Edit `active-sessions-script.json` to change narration or actions. Each segment has:

- `narration` — text spoken by TTS
- `action` — one of `navigate`, `click`, `scroll`, or `wait`
- `pause_after_ms` — minimum pause after the action (audio duration may extend this)
- `selector` — CSS selector for `click` actions
- `url` — URL for `navigate` actions
- `pixels` — scroll distance for `scroll` actions

## Known limitations

- **Piper TTS voice quality** — the `en_US-lessac-medium` voice is functional but sounds robotic. A higher-quality TTS engine (e.g., a cloud API) could be swapped in by replacing `generate_audio_clips()`.
- **Active sessions required** — the current script clicks a session card, so at least one active/recent session must exist.
- **No cursor visualization** — Playwright's headless browser doesn't show a mouse cursor in the video.
