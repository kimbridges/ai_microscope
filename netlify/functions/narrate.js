// Proxies a narration request to the Gemini API.
// The API key lives ONLY in the GEMINI_KEY environment variable
// (Netlify dashboard), never in the client.
//
// Env vars used:
//   GEMINI_KEY    (required) - the Google Generative Language API key
//   ALLOWED_HOST  (optional) - e.g. "aimicroscope.netlify.app"; if set,
//                              requests whose Referer/Origin don't include
//                              it are rejected. Leave unset during testing.

function originAllowed(event) {
  const allowed = process.env.ALLOWED_HOST;
  if (!allowed) return true; // not configured yet -> don't block
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

  const key = process.env.GEMINI_KEY;
  if (!key) {
    return { statusCode: 500, body: "Server is missing GEMINI_KEY" };
  }

  let prompt;
  try {
    ({ prompt } = JSON.parse(event.body || "{}"));
  } catch (e) {
    return { statusCode: 400, body: "Bad JSON body" };
  }
  if (!prompt) {
    return { statusCode: 400, body: "Missing 'prompt'" };
  }

  try {
    const resp = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${key}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
      }
    );
    const data = await resp.json();
    const text =
      (data &&
        data.candidates &&
        data.candidates[0] &&
        data.candidates[0].content &&
        data.candidates[0].content.parts &&
        data.candidates[0].content.parts[0] &&
        data.candidates[0].content.parts[0].text) || "";
    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text.trim() })
    };
  } catch (e) {
    return { statusCode: 502, body: "Upstream error contacting Gemini" };
  }
};
