// Proxies a text-to-speech request to the ElevenLabs API and returns
// the MP3 audio. The API key lives ONLY in the ELEVEN_KEY environment
// variable (Netlify dashboard), never in the client.
//
// Env vars used:
//   ELEVEN_KEY    (required) - the ElevenLabs API key
//   ALLOWED_HOST  (optional) - same origin check as narrate.js

const DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"; // "Rachel"

function originAllowed(event) {
  const allowed = process.env.ALLOWED_HOST;
  if (!allowed) return true;
  const ref = event.headers.referer || event.headers.origin || "";
  return ref.includes(allowed);
}

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, body: "Method Not Allowed" };
  }
  if (!originAllowed(event)) {
    return { statusCode: 403, body: "Forbidden" };
  }

  const key = process.env.ELEVEN_KEY;
  if (!key) {
    return { statusCode: 500, body: "Server is missing ELEVEN_KEY" };
  }

  let text, voiceId, model;
  try {
    ({ text, voiceId, model } = JSON.parse(event.body || "{}"));
  } catch (e) {
    return { statusCode: 400, body: "Bad JSON body" };
  }
  if (!text) {
    return { statusCode: 400, body: "Missing 'text'" };
  }
  // Allow the caller to pick the model. Narration uses the fast flash model by
  // default; pronunciation uses turbo v2 (the model that honours phoneme tags).
  const ALLOWED_MODELS = ["eleven_flash_v2_5", "eleven_turbo_v2"];
  const modelId = ALLOWED_MODELS.includes(model) ? model : "eleven_flash_v2_5";

  try {
    const resp = await fetch(
      `https://api.elevenlabs.io/v1/text-to-speech/${voiceId || DEFAULT_VOICE}`,
      {
        method: "POST",
        headers: {
          Accept: "audio/mpeg",
          "Content-Type": "application/json",
          "xi-api-key": key
        },
        body: JSON.stringify({
          text: text,
          model_id: modelId,
          voice_settings: { stability: 0.5, similarity_boost: 0.75 }
        })
      }
    );
    if (!resp.ok) {
      return { statusCode: 502, body: "Upstream error contacting ElevenLabs" };
    }
    const buf = Buffer.from(await resp.arrayBuffer());
    return {
      statusCode: 200,
      headers: { "Content-Type": "audio/mpeg" },
      body: buf.toString("base64"),
      isBase64Encoded: true
    };
  } catch (e) {
    return { statusCode: 502, body: "Upstream error contacting ElevenLabs" };
  }
};
