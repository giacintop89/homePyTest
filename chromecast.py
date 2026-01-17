import sys
import subprocess
import time
import pychromecast

SPEAKER_NAME = "Speaker Cucina"
YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

def yt_audio_url(url: str) -> str:
    # Prefer m4a if possible; fallback to bestaudio
    out = subprocess.check_output(
        [sys.executable, "-m", "yt_dlp", "-f", "bestaudio[ext=m4a]/bestaudio", "-g", url],
        text=True
    ).strip()
    if not out.startswith("http"):
        raise RuntimeError(f"yt-dlp did not return a URL:\n{out}")
    return out

def main():
    audio_url = yt_audio_url(YOUTUBE_URL)
    print("Audio URL:", audio_url[:120], "...")

    chromecasts, browser = pychromecast.get_chromecasts()
    try:
        cast = next(c for c in chromecasts if c.name == SPEAKER_NAME)
        cast.wait()

        cast.set_volume(0.5)

        mc = cast.media_controller
        mc.play_media(audio_url, content_type="audio/mp4")
        mc.block_until_active()

        print("Now casting on:", SPEAKER_NAME, "| App:", cast.app_display_name)
        time.sleep(10)

    finally:
        # IMPORTANT: stop discovery only after we're done
        pychromecast.discovery.stop_discovery(browser)
        try:
            cast.disconnect()
        except Exception:
            pass

if __name__ == "__main__":
    main()
