export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  const videoId = req.query.v;
  if (!videoId) return res.json({ status: "ok" });

  const errors = [];

  // 시도 1: WEB_EMBEDDED_PLAYER (iframe embed 방식)
  try {
    const t = await fetchInnertubeClient(videoId, {
      clientName: "WEB_EMBEDDED_PLAYER",
      clientVersion: "2.20240201.00.00",
      hl: "en",
    }, { embedUrl: "https://www.youtube.com" });
    return res.json({ transcript: t, video_id: videoId });
  } catch (e) { errors.push("WEB_EMBED:" + e.message); }

  // 시도 2: ANDROID_EMBEDDED_PLAYER
  try {
    const t = await fetchInnertubeClient(videoId, {
      clientName: "ANDROID_EMBEDDED_PLAYER",
      clientVersion: "19.09.37",
      androidSdkVersion: 30,
      hl: "en",
    });
    return res.json({ transcript: t, video_id: videoId });
  } catch (e) { errors.push("ANDROID_EMBED:" + e.message); }

  // 시도 3: WEB (일반 웹)
  try {
    const t = await fetchInnertubeClient(videoId, {
      clientName: "WEB",
      clientVersion: "2.20240201.00.00",
      hl: "en",
    });
    return res.json({ transcript: t, video_id: videoId });
  } catch (e) { errors.push("WEB:" + e.message); }

  res.status(500).json({ error: errors.join(" | ") });
}

async function fetchInnertubeClient(videoId, client, thirdParty = null) {
  const context = { client };
  if (thirdParty) context.thirdParty = thirdParty;

  const resp = await fetch("https://www.youtube.com/youtubei/v1/player", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
      "Origin": "https://www.youtube.com",
      "Referer": "https://www.youtube.com/",
    },
    body: JSON.stringify({ videoId, context }),
  });

  const data = await resp.json();
  const status = data?.playabilityStatus?.status;
  if (status && status !== "OK") throw new Error(`playability:${status}`);

  const tracks = data?.captions?.playerCaptionsTracklistRenderer?.captionTracks;
  if (!tracks?.length) throw new Error(`자막없음(keys:${Object.keys(data).join(",")})`);

  const track = tracks.find(t => t.languageCode?.startsWith("en")) || tracks[0];
  if (!track?.baseUrl) throw new Error("URL없음");

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
