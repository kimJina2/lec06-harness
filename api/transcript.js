export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");

  const videoId = req.query.v;
  if (!videoId) return res.json({ status: "ok" });

  try {
    const transcript = await fetchViaInnertube(videoId);
    res.json({ transcript, video_id: videoId });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}

async function fetchViaInnertube(videoId) {
  // Android 클라이언트 — 클라우드 IP에서도 차단 적음
  const body = {
    videoId,
    context: {
      client: {
        clientName: "ANDROID",
        clientVersion: "19.09.37",
        androidSdkVersion: 30,
        hl: "en",
      },
    },
  };

  const resp = await fetch(
    "https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
        "X-YouTube-Client-Name": "3",
        "X-YouTube-Client-Version": "19.09.37",
      },
      body: JSON.stringify(body),
    }
  );

  if (!resp.ok) throw new Error(`InnerTube HTTP ${resp.status}`);
  const data = await resp.json();

  const tracks = data?.captions?.playerCaptionsTracklistRenderer?.captionTracks;
  if (!tracks?.length) throw new Error("자막 없음");

  const track = tracks.find((t) => t.languageCode?.startsWith("en")) || tracks[0];
  if (!track?.baseUrl) throw new Error("자막 URL 없음");

  const vttResp = await fetch(track.baseUrl + "&fmt=vtt");
  const vtt = await vttResp.text();
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
