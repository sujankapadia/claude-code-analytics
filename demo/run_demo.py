#!/usr/bin/env python3
"""Automated demo video pipeline.

Generates a narrated demo video by:
1. Creating TTS audio clips with Piper
2. Recording browser interactions with Playwright
3. Merging audio + video with ffmpeg
"""

import json
import subprocess
import sys
import time
from pathlib import Path

DEMO_DIR = Path(__file__).parent
OUTPUT_DIR = DEMO_DIR / "output"
PIPER_MODEL = str(DEMO_DIR / "models" / "en_US-lessac-medium.onnx")


def generate_audio_clips(segments: list[dict]) -> list[Path]:
    """Generate WAV audio clips for each segment's narration using Piper TTS."""
    clips = []
    for i, seg in enumerate(segments):
        output_path = OUTPUT_DIR / f"segment_{i}.wav"
        text = seg["narration"]
        print(f"  Generating audio for segment {i}: {text[:50]}...")
        result = subprocess.run(  # nosec B607
            ["piper", "--model", PIPER_MODEL, "--output_file", str(output_path)],
            input=text,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            print(f"  Piper error: {result.stderr}", file=sys.stderr)
            sys.exit(1)
        clips.append(output_path)
    return clips


def get_audio_duration(path: Path) -> float:
    """Get duration of an audio file in seconds using ffprobe."""
    result = subprocess.run(  # nosec B607
        [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def record_browser_video(
    segments: list[dict], clip_durations: list[float], resolution: dict
) -> Path:
    """Record browser interactions using Playwright with video capture."""
    from playwright.sync_api import sync_playwright

    video_path = None
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={
                "width": resolution["width"],
                "height": resolution["height"],
            },
            record_video_dir=str(OUTPUT_DIR),
            record_video_size={
                "width": resolution["width"],
                "height": resolution["height"],
            },
        )
        page = context.new_page()

        for i, seg in enumerate(segments):
            action = seg["action"]
            pause_ms = seg.get("pause_after_ms", 0)
            audio_duration_ms = clip_durations[i] * 1000
            wait_ms = max(audio_duration_ms, pause_ms)

            print(f"  Segment {i}: action={action}, wait={wait_ms:.0f}ms")

            if action == "navigate":
                page.goto(seg["url"], wait_until="domcontentloaded")
                page.wait_for_load_state("load")
                # Give React time to render
                time.sleep(1)
            elif action == "click":
                page.wait_for_selector(seg["selector"], timeout=10000)
                page.click(seg["selector"])
            elif action == "scroll":
                page.evaluate(f"window.scrollBy(0, {seg.get('pixels', 300)})")
            elif action == "wait":
                pass

            # Wait for the duration of the narration + any extra pause
            time.sleep(wait_ms / 1000)

        # Close context to finalize video
        video = page.video
        if video is None:
            print("Error: no video was recorded", file=sys.stderr)
            sys.exit(1)
        video_path = video.path()
        context.close()
        browser.close()

    return Path(video_path)


def combine_audio_video(
    video_path: Path,
    audio_clips: list[Path],
    clip_durations: list[float],
    segments: list[dict],
    output_path: Path,
) -> None:
    """Merge audio clips with video into final MP4 using ffmpeg."""
    # Build a combined audio track with silence gaps matching video timing
    concat_list = OUTPUT_DIR / "audio_concat.txt"
    silence_path = OUTPUT_DIR / "silence.wav"

    # Create a short silence file (100ms) for use as padding
    subprocess.run(  # nosec B607
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=22050:cl=mono",
            "-t",
            "0.1",
            silence_path,
        ],
        capture_output=True,
    )

    # For each segment, compute how much silence to insert after the clip
    # to fill the gap until the next segment starts
    entries = []
    for i, clip in enumerate(audio_clips):
        entries.append(f"file '{clip.resolve()}'")
        pause_ms = segments[i].get("pause_after_ms", 0)
        audio_ms = clip_durations[i] * 1000
        gap_ms = max(0, max(audio_ms, pause_ms) - audio_ms)
        if gap_ms > 0:
            # Create a silence file for this specific gap
            gap_silence = OUTPUT_DIR / f"silence_{i}.wav"
            subprocess.run(  # nosec B607
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=22050:cl=mono",
                    "-t",
                    str(gap_ms / 1000),
                    str(gap_silence),
                ],
                capture_output=True,
            )
            entries.append(f"file '{gap_silence.resolve()}'")

    concat_list.write_text("\n".join(entries))

    # Concatenate all audio clips
    combined_audio = OUTPUT_DIR / "combined_audio.wav"
    subprocess.run(  # nosec B607
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(combined_audio),
        ],
        capture_output=True,
    )

    # Merge video + audio into final MP4
    print(f"  Merging video + audio into {output_path}...")
    result = subprocess.run(  # nosec B607
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(combined_audio),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  ffmpeg error: {result.stderr}", file=sys.stderr)
        sys.exit(1)


def main():
    script_path = DEMO_DIR / "active-sessions-script.json"
    if not script_path.exists():
        print(f"Script not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    script = json.loads(script_path.read_text())
    segments = script["segments"]
    resolution = script["resolution"]

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Phase A: Generate audio clips
    print("Phase A: Generating audio clips with Piper TTS...")
    audio_clips = generate_audio_clips(segments)
    clip_durations = [get_audio_duration(clip) for clip in audio_clips]
    for i, dur in enumerate(clip_durations):
        print(f"  Segment {i} audio: {dur:.2f}s")

    # Phase B: Record browser video
    print("\nPhase B: Recording browser with Playwright...")
    video_path = record_browser_video(segments, clip_durations, resolution)
    print(f"  Video saved: {video_path}")

    # Phase C: Combine audio + video
    print("\nPhase C: Combining audio + video with ffmpeg...")
    output_path = OUTPUT_DIR / "active-sessions-demo.mp4"
    combine_audio_video(video_path, audio_clips, clip_durations, segments, output_path)
    print(f"\nDone! Output: {output_path}")


if __name__ == "__main__":
    main()
