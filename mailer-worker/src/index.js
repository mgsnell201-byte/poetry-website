const JSON_HEADERS = {
  "Content-Type": "application/json",
  "Cache-Control": "no-store",
};

const VALID_VOTE_ID = /^[a-z0-9][a-z0-9/_-]{0,159}$/;
const VALID_CHOICES = new Set(["", "up", "down"]);

const ALLOWED_ORIGINS = new Set([
  "https://osmoticpoet.com",
  "https://www.osmoticpoet.com",
  "https://osmoticpoet.pages.dev",
]);

const RATE_BUCKETS = new Map();

function isAllowedOrigin(request) {
  const origin = request.headers.get("Origin");
  if (!origin) return false;
  return ALLOWED_ORIGINS.has(origin);
}

function isRateLimited(request, keyPrefix, maxRequests, windowMs) {
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const key = `${keyPrefix}:${ip}`;
  const now = Date.now();
  if (RATE_BUCKETS.size > 2000) {
    for (const [k, v] of RATE_BUCKETS) {
      if (now >= v.resetAt) RATE_BUCKETS.delete(k);
    }
  }
  const entry = RATE_BUCKETS.get(key);
  if (!entry || now >= entry.resetAt) {
    RATE_BUCKETS.set(key, { count: 1, resetAt: now + windowMs });
    return false;
  }
  entry.count += 1;
  return entry.count > maxRequests;
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });
}

async function handleVotes(request, env) {
  if (request.method === "GET") {
    const id = (new URL(request.url).searchParams.get("id") || "").trim();
    if (!VALID_VOTE_ID.test(id)) {
      return jsonResponse({ error: "Invalid id" }, 400);
    }
    const row = await env.VOTES_DB
      .prepare("SELECT up, down FROM votes WHERE id = ?")
      .bind(id)
      .first();
    return jsonResponse({ up: row?.up ?? 0, down: row?.down ?? 0 });
  }

  if (request.method !== "POST") {
    return jsonResponse({ error: "Method not allowed" }, 405);
  }
  if (!isAllowedOrigin(request)) {
    return jsonResponse({ error: "Forbidden origin" }, 403);
  }
  if (isRateLimited(request, "votes", 30, 60_000)) {
    return jsonResponse({ error: "Too many requests" }, 429);
  }

  let payload;
  try {
    payload = await request.json();
  } catch {
    return jsonResponse({ error: "Invalid JSON" }, 400);
  }

  const id = String(payload?.id || "").trim();
  const prev = String(payload?.prev || "");
  const next = String(payload?.next || "");
  if (!VALID_VOTE_ID.test(id) || !VALID_CHOICES.has(prev) || !VALID_CHOICES.has(next)) {
    return jsonResponse({ error: "Invalid vote payload" }, 400);
  }

  const dUp = (next === "up" ? 1 : 0) - (prev === "up" ? 1 : 0);
  const dDown = (next === "down" ? 1 : 0) - (prev === "down" ? 1 : 0);

  if (dUp !== 0 || dDown !== 0) {
    await env.VOTES_DB.prepare(
      `INSERT INTO votes (id, up, down)
       VALUES (?, MAX(0, ?), MAX(0, ?))
       ON CONFLICT(id) DO UPDATE SET
         up = MAX(0, up + ?),
         down = MAX(0, down + ?)`
    )
      .bind(id, dUp, dDown, dUp, dDown)
      .run();
  }

  const row = await env.VOTES_DB
    .prepare("SELECT up, down FROM votes WHERE id = ?")
    .bind(id)
    .first();
  return jsonResponse({ up: row?.up ?? 0, down: row?.down ?? 0 });
}

async function handleNote(request, env) {
  if (request.method !== "POST") {
    return jsonResponse({ success: false, message: "Method not allowed" }, 405);
  }
  if (!isAllowedOrigin(request)) {
    return jsonResponse({ success: false, message: "Forbidden origin." }, 403);
  }
  if (isRateLimited(request, "note", 5, 600_000)) {
    return jsonResponse({ success: false, message: "Too many notes sent recently. Please wait a few minutes." }, 429);
  }

  const formData = await request.formData();
  if (formData.get("botcheck")) {
    return jsonResponse({ success: true });
  }

  const name = String(formData.get("name") || "").trim().slice(0, 120);
  const email = String(formData.get("email") || "").trim().slice(0, 160);
  const message = String(formData.get("message") || "").trim().slice(0, 4000);
  const rawSubject = String(formData.get("subject") || "New Note from OsmoticPoet");
  const subject = rawSubject.replace(/[\r\n]+/g, " ").trim().slice(0, 180);

  if (!name || !message) {
    return jsonResponse({ success: false, message: "Please enter both your name and a comment." }, 400);
  }
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return jsonResponse(
      { success: false, message: "Please enter a valid email address or leave it blank." },
      400
    );
  }

  const escapeHtml = (s) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  const payload = {
    to: "mgsnell201@gmail.com",
    from: "OsmoticPoet Notes <notes@osmoticpoet.com>",
    subject,
    text: `Name: ${name}\nEmail: ${email || "(not provided)"}\n\nMessage:\n${message}`,
    html: `<div style="font-family: Georgia, serif; max-width: 600px; line-height: 1.6; color: #222;"><h2 style="margin: 0 0 12px;">${escapeHtml(subject)}</h2><p><strong>Name:</strong> ${escapeHtml(name)}<br><strong>Email:</strong> ${escapeHtml(email || "(not provided)")}</p><hr style="border: 0; border-top: 1px solid #ddd; margin: 16px 0;"><p style="white-space: pre-wrap;">${escapeHtml(message)}</p></div>`,
  };
  if (email) payload.replyTo = email;

  await env.EMAIL.send(payload);
  return jsonResponse({ success: true });
}

export default {
  async fetch(request, env) {
    try {
      const { pathname } = new URL(request.url);
      if (pathname === "/api/votes") {
        return await handleVotes(request, env);
      }
      return await handleNote(request, env);
    } catch {
      return jsonResponse(
        { success: false, message: "Could not complete request right now." },
        500
      );
    }
  },
};
