from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.request
from urllib.parse import urlparse, parse_qs

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def _parse_vtt(vtt: str) -> str:
    texts = []
    for line in vtt.split("\n"):
        line = line.strip()
        if not line or "-->" in line or line.startswith("WEBVTT") or re.match(r"^\d+$", line):
            continue
        text = re.sub(r"<[^>]+>", "", line).strip()
        if text and (not texts or texts[-1] != text):
            texts.append(text)
    return " ".join(texts)


def _fetch(video_id: str) -> str:
    req = urllib.request.Request(
        f"https://www.youtube.com/watch?v={video_id}&hl=en",
        headers={"User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        html = r.read().decode("utf-8", errors="ignore")

    m = re.search(r'"captionTracks":\s*(\[.*?\])', html)
    if not m:
        raise ValueError("자막 없음")

    tracks = json.loads(m.group(1))
    track = next((t for t in tracks if t.get("languageCode", "").startswith("en")), None)
    if not track:
        track = tracks[0] if tracks else None
    if not track or not track.get("baseUrl"):
        raise ValueError("자막 URL 없음")

    vtt_req = urllib.request.Request(track["baseUrl"] + "&fmt=vtt", headers={"User-Agent": UA})
    with urllib.request.urlopen(vtt_req, timeout=15) as r:
        vtt = r.read().decode("utf-8", errors="ignore")

    return _parse_vtt(vtt)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        video_id = (params.get("v") or [None])[0]

        if not video_id:
            self._respond(400, {"error": "Missing v parameter"})
            return
        try:
            transcript = _fetch(video_id)
            self._respond(200, {"transcript": transcript, "video_id": video_id})
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _respond(self, code: int, body: dict):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass
