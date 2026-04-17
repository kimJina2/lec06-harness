export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  const videoId = req.query.v;
  if (!videoId) return res.json({ status: "ok" });

  const errors = [];

  // 시도 1: TV embedded 클라이언트
  try {
    const t = await fetchInnertube(videoId, "TVHTML5_SIMPLY_EMBEDDED_PLAYER", "2.0");
    return res.json({ transcript: t, video_id: videoId });
  } catch (e) { errors.push("TV:" + e.message); }

  // 시도 2: iOS 클라이언트
  try {
    const t = await fetchInnertube(videoId, "IOS", "19.09.3");
    return res.json({ transcript: t, video_id: videoId });
  } catch (e) { errors.push("iOS:" + e.message); }

  // 시도 3: timedtext 직접 접근
  try {
    const t = await fetchTimedtext(videoId);
    return res.json({ transcript: t, video_id: videoId });
  } catch (e) { errors.push("timedtext:" + e.message); }

  res.status(500).json({ error: errors.join(" | ") });
}

async function fetchInnertube(videoId, clientName, clientVersion) {
  const resp = await fetch("https://www.youtube.com/youtubei/v1/player", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      videoId,
      context: { client: { clientName, clientVersion, hl: "en" } },
    }),
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const data = await resp.json();
  const tracks = data?.captions?.playerCaptionsTracklistRenderer?.captionTracks;
  if (!tracks?.length) throw new Error("자막 없음");
  const track = tracks.find(t => t.languageCode?.startsWith("en")) || tracks[0];
  if (!track?.baseUrl) throw new Error("URL 없음");
  const vtt = await (await fetch(track.baseUrl + "&fmt=vtt")).text();
  return parseVtt(vtt);
}

async function fetchTimedtext(videoId) {
  // 자막 목록 먼저 가져오기
  const listResp = await fetch(
    `https://www.youtube.com/api/timedtext?v=${videoId}&type=list&fmt=json3`
  );
  if (!listResp.ok) throw new Error(`HTTP ${listResp.status}`);
  const list = await listResp.json();
  const tracks = list?.captions?.playerCaptionsTracklistRenderer?.captionTracks;
  if (!tracks?.length) throw new Error("자막 없음");
  const track = tracks.find(t => t.languageCode?.startsWith("en")) || tracks[0];
  const vtt = await (await fetch(track.baseUrl + "&fmt=vtt")).text();
  return parseVtt(vtt);
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
