# Demo Video Pipeline

Automated narrated demo video generation — fully scripted, no screen recording or manual voiceover needed.

## Pipeline Architecture

```
Script (JSON) → TTS engine (WAV clips) → Playwright (browser video) → ffmpeg (final MP4)
```

1. A **demo script** (`active-sessions-script.json`) defines segments with narration text and browser actions
2. A **TTS engine** generates a WAV audio clip for each segment's narration (see [TTS Providers](#tts-providers) below)
3. **Playwright** launches a browser with `recordVideo`, executes each action, and sleeps for the duration of the corresponding audio clip so video and narration stay in sync
4. **ffmpeg** concatenates audio clips (with silence gaps for pauses) and merges the combined audio track with the browser video into a final MP4

## Prerequisites

```bash
# Python dependencies (core)
pip install playwright

# Browser binary for Playwright
playwright install chromium

# ffmpeg (brew install ffmpeg) — provides both ffmpeg and ffprobe
```

Plus a TTS provider — see setup instructions below.

## TTS Providers

The pipeline supports swappable TTS backends selected via `--tts` flag. Three are available:

### Piper TTS (local, free, robotic)

Runs entirely offline. Fast and free, but the voice sounds noticeably synthetic.

```bash
# Install
pip install piper-tts pathvalidate

# Download the voice model (~60 MB, gitignored)
python -m piper.download_voices --download-dir demo/models en_US-lessac-medium
```

- Voice model: `en_US-lessac-medium` (also available in `high` quality)
- Model files land in `demo/models/` (gitignored)
- No API keys or network access required

### Google Cloud TTS (cloud, free tier, natural-sounding)

Uses Google's WaveNet voices — significantly more human-sounding than Piper.

**Free tier:** 1 million WaveNet characters/month, 4 million standard characters/month. A typical demo script is ~300 characters, so the free tier covers thousands of renders.

```bash
# Install gcloud CLI
brew install google-cloud-sdk

# Authenticate and set project
gcloud auth login
gcloud config set project <YOUR_PROJECT_ID>

# Enable the TTS API
gcloud services enable texttospeech.googleapis.com
```

- Voice: `en-US-WaveNet-D` (male) — see [full voice list](https://cloud.google.com/text-to-speech/docs/voices)
- Requires billing enabled on the GCP project (free tier still applies)
- API call: `POST https://texttospeech.googleapis.com/v1/text:synthesize` with quota project header

**Quick test:**
```bash
ACCESS_TOKEN=$(gcloud auth print-access-token)
curl -s -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "x-goog-user-project: <YOUR_PROJECT_ID>" \
  -d '{
    "input": { "text": "Hello, this is a test of Google Cloud Text to Speech." },
    "voice": { "languageCode": "en-US", "name": "en-US-WaveNet-D" },
    "audioConfig": { "audioEncoding": "LINEAR16" }
  }' \
  "https://texttospeech.googleapis.com/v1/text:synthesize" \
  | python3 -c "import sys,json,base64; data=json.load(sys.stdin); open('demo/output/test_gcloud.wav','wb').write(base64.b64decode(data['audioContent']))"
```

### ElevenLabs (cloud, paid, highest quality)

Uses ElevenLabs' voice cloning and synthesis — the most natural-sounding option.

Add credentials to `demo/.env`:

```env
ELEVENLABS_API_KEY=your-key-here
ELEVENLABS_VOICE_ID=your-voice-id-here

# Voice tuning (all optional, defaults shown)
ELEVENLABS_STABILITY=0.4
ELEVENLABS_SIMILARITY_BOOST=0.75
ELEVENLABS_STYLE=0.3
ELEVENLABS_USE_SPEAKER_BOOST=true
```

- `stability` (0.0–1.0) — lower = more expressive, higher = monotone
- `similarity_boost` (0.0–1.0) — how closely it matches the original voice
- `style` (0.0–1.0) — style exaggeration for more expressiveness
- `use_speaker_boost` — enhances speaker similarity
- Requires a paid plan for cloned voices; pre-made voices work on free tier
- The `.env` file is gitignored

### Comparison

| Provider | Quality | Cost | Latency | Offline |
|----------|---------|------|---------|---------|
| Piper TTS | Robotic | Free | ~1s/segment | Yes |
| Google Cloud TTS (WaveNet) | Natural | Free tier (1M chars/mo) | ~2s/segment | No |
| ElevenLabs | Most natural | Paid (~$5/mo starter) | ~2s/segment | No |

## Usage

1. Start the API and frontend dev servers:
   ```bash
   claude-code-api                  # port 8000
   cd frontend && npm run dev       # port 5173
   ```

2. Make sure you have at least one active Claude Code session running (the demo clicks a session card).

3. Run the pipeline:
   ```bash
   python demo/run_demo.py --tts elevenlabs   # or: piper, google
   ```

4. Output lands in `demo/output/active-sessions-demo.mp4`.

## How it works

### Phase A: Audio generation
For each segment, narration text is sent to the selected TTS provider to generate an audio clip. Clip durations are measured with `ffprobe` to calculate Playwright timing. Non-WAV outputs (e.g. MP3 from ElevenLabs) are automatically converted to WAV before merging.

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

- **Active sessions required** — the current script clicks a session card, so at least one active/recent session must exist.
- **No cursor visualization** — Playwright's headless browser doesn't show a mouse cursor in the video.
