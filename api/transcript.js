export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");

  const videoId = req.query.v;
  if (!videoId) {
    return res.json({ status: "ok", usage: "?v=VIDEO_ID" });
  }

  try {
    const transcript = await fetchTranscript(videoId);
    res.json({ transcript, video_id: videoId });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}

async function fetchTranscript(videoId) {
  const ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36";
  const resp = await fetch(`https://www.youtube.com/watch?v=${videoId}&hl=en`, {
    headers: { "User-Agent": ua },
  });
  if (!resp.ok) throw new Error(`YouTube HTTP ${resp.status}`);
  const html = await resp.text();

  const m = html.match(/"captionTracks":\s*(\[.*?\])/);
  if (!m) throw new Error("자막 없음");

  const tracks = JSON.parse(m[1]);
  const track = tracks.find(t => t.languageCode?.startsWith("en")) || tracks[0];
  if (!track?.baseUrl) throw new Error("자막 URL 없음");

  const vttResp = await fetch(track.baseUrl + "&fmt=vtt", { headers: { "User-Agent": ua } });
  const vtt = await vttResp.text();

  return parseVtt(vtt);
}

function parseVtt(vtt) {
  const lines = vtt.split("\n");
  const texts = [];
  for (const raw of lines) {
    const line = raw.trim();
    if (!line || line.includes("-->") || line.startsWith("WEBVTT") || /^\d+$/.test(line)) continue;
    const text = line.replace(/<[^>]+>/g, "").trim();
    if (text && texts[texts.length - 1] !== text) texts.push(text);
  }
  return texts.join(" ");
}
