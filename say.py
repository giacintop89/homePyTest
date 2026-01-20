import socket
import threading
import time
import asyncio
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial

import pychromecast
from pychromecast.error import RequestFailed
import edge_tts

# ====== CONFIG ======
CAST_NAME = "Speaker Cucina"          # <- EXACT name from discovery
TEXT = "Ciao."  # Text to say
VOICE = "it-IT-DiegoNeural"          # try: it-IT-ElsaNeural, it-IT-IsabellaNeural, it-IT-DiegoNeural
RATE = "+5%"                         # e.g. "-10%", "+15%"
PITCH = "-66Hz"                       # e.g. "+20Hz", "-10Hz"
VOLUME = "+0%"                       # e.g. "+10%", "-10%"

PORT = 8765
CAST_VOLUME = 0.7                    # 0.0 - 1.0
MAX_WAIT_SECONDS = 20
# ====================

mp3_requested = threading.Event()


class LoggingHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        print("HTTP:", format % args)

    def do_GET(self):
        if self.path == "/say.mp3":
            mp3_requested.set()
        super().do_GET()


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def serve_folder(folder: Path, port: int) -> ThreadingHTTPServer:
    handler = partial(LoggingHandler, directory=str(folder))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=False)
    t.start()
    return httpd


def friendly_name(cast) -> str | None:
    return getattr(cast, "name", None) or getattr(getattr(cast, "cast_info", None), "friendly_name", None)


async def make_tts_mp3(out_path: Path) -> None:
    communicate = edge_tts.Communicate(
        TEXT,
        voice=VOICE,
        rate=RATE,
        pitch=PITCH,
        volume=VOLUME,
    )
    await communicate.save(str(out_path))


def main() -> None:
    # 1) Generate MP3 with Edge TTS
    out_dir = Path(__file__).resolve().parent / "tts_out"
    out_dir.mkdir(exist_ok=True)
    mp3_path = out_dir / "say.mp3"

    asyncio.run(make_tts_mp3(mp3_path))

    if not mp3_path.exists():
        raise RuntimeError(f"MP3 was not created: {mp3_path}")

    print("MP3 path:", mp3_path)

    # 2) Serve MP3
    httpd = serve_folder(out_dir, PORT)
    media_url = f"http://{get_local_ip()}:{PORT}/{mp3_path.name}"
    print("Serving:", media_url)

    # 3) Discover Cast devices (keep discovery running while connecting/starting)
    chromecasts, browser = pychromecast.get_chromecasts()

    try:
        print("Discovered Cast devices:")
        for c in chromecasts:
            print(" -", friendly_name(c))

        cast = next((c for c in chromecasts if friendly_name(c) == CAST_NAME), None)
        if not cast:
            raise RuntimeError(f'Cast device "{CAST_NAME}" not found.')

        cast.wait(timeout=15)
        cast.set_volume(CAST_VOLUME)

        mc = cast.media_controller
        try:
            mc.stop()
        except RequestFailed:
            pass

        # 4) Play
        mc.play_media(media_url, content_type="audio/mpeg")
        mc.block_until_active(timeout=15)
        print("Cast started. Waiting for speaker to request /say.mp3 ...")

        if mp3_requested.wait(timeout=10):
            print("Speaker requested /say.mp3 ✅ (you should see a 200 below)")
        else:
            print("No request seen for /say.mp3 ❌ (firewall/network isolation likely)")

        time.sleep(MAX_WAIT_SECONDS)

    finally:
        try:
            browser.stop_discovery()
        except Exception:
            pass
        try:
            httpd.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
