export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  const videoId = req.query.v;
  if (!videoId) return res.json({ status: "ok" });

  const errors = [];

  // 시도 1: timedtext 직접 (lang=en)
  for (const lang of ["en", "en-US", "ko", ""]) {
    try {
      const url = `https://www.youtube.com/api/timedtext?v=${videoId}&lang=${lang}&fmt=vtt`;
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const vtt = await r.text();
      if (vtt.includes("WEBVTT")) {
        return res.json({ transcript: parseVtt(vtt), video_id: videoId });
      }
    } catch (e) { errors.push(`timedtext-${lang}:${e.message}`); }
  }

  // 시도 2: TV embedded InnerTube — 구조 디버그
  try {
    const resp = await fetch("https://www.youtube.com/youtubei/v1/player", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        videoId,
        context: { client: { clientName: "TVHTML5_SIMPLY_EMBEDDED_PLAYER", clientVersion: "2.0", hl: "en" } },
      }),
    });
    const data = await resp.json();
    const tracks = data?.captions?.playerCaptionsTracklistRenderer?.captionTracks;
    if (tracks?.length) {
      const track = tracks.find(t => t.languageCode?.startsWith("en")) || tracks[0];
      const vtt = await (await fetch(track.baseUrl + "&fmt=vtt")).text();
      return res.json({ transcript: parseVtt(vtt), video_id: videoId });
    }
    // 디버그: 응답 키 확인
    errors.push("TV:keys=" + Object.keys(data).join(","));
  } catch (e) { errors.push("TV:" + e.message); }

  res.status(500).json({ error: errors.join(" | ") });
}

function parseVtt(vtt) {
  const texts = [];
  for (const raw of vtt.split("\n")) {
    const line = raw.trim();
    if (!line || line.includes("-->") || line.startsWith("WEBVTT") || /^\d+$/.test(line)) continue;
    const text = line.replace(/<[^>]+>/g, "").trim();
    if (text && texts[texts.length - 1] !== text) texts.push(text);
  }
  return texts.join(" ");
}
