export async function onRequestPost(context) {
  const { request, env } = context;
  const headers = { "Content-Type": "application/json" };

  try {
    // Basic origin check against automated off-site spam
    const origin = request.headers.get("Origin") || "";
    if (
      origin &&
      !origin.includes("osmoticpoet.com") &&
      !origin.includes("osmoticpoet.pages.dev") &&
      !origin.includes("localhost") &&
      !origin.includes("127.0.0.1")
    ) {
      return new Response(JSON.stringify({ success: false, message: "Forbidden origin." }), { status: 403, headers });
    }

    const formData = await request.formData();

    // Honeypot spam trap: bots fill hidden fields; silently accept without sending
    if (formData.get("botcheck")) {
      return new Response(JSON.stringify({ success: true }), { status: 200, headers });
    }

    const name = String(formData.get("name") || "").trim().slice(0, 120);
    const email = String(formData.get("email") || "").trim().slice(0, 160);
    const message = String(formData.get("message") || "").trim().slice(0, 4000);
    const rawSubject = String(formData.get("subject") || "New Note from OsmoticPoet");
    const subject = rawSubject.replace(/[\r\n]+/g, " ").trim().slice(0, 180);

    if (!name || !message) {
      return new Response(
        JSON.stringify({ success: false, message: "Please enter both your name and a comment." }),
        { status: 400, headers }
      );
    }

    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return new Response(
        JSON.stringify({ success: false, message: "Please enter a valid email address or leave it blank." }),
        { status: 400, headers }
      );
    }

    const escapeHtml = (s) =>
      s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

    const textBody = [
      `Name: ${name}`,
      `Email: ${email || "(not provided)"}`,
      "",
      "Message:",
      message,
    ].join("\n");

    const htmlBody = `
      <div style="font-family: Georgia, serif; max-width: 600px; line-height: 1.6; color: #222;">
        <h2 style="margin: 0 0 12px;">${escapeHtml(subject)}</h2>
        <p><strong>Name:</strong> ${escapeHtml(name)}<br>
        <strong>Email:</strong> ${escapeHtml(email || "(not provided)")}</p>
        <hr style="border: 0; border-top: 1px solid #ddd; margin: 16px 0;">
        <p style="white-space: pre-wrap;">${escapeHtml(message)}</p>
      </div>
    `;

    const payload = {
      to: "mgsnell201@gmail.com",
      from: "OsmoticPoet Notes <notes@osmoticpoet.com>",
      subject,
      text: textBody,
      html: htmlBody,
    };
    if (email) {
      payload.replyTo = email;
    }

    await env.EMAIL.send(payload);
    return new Response(JSON.stringify({ success: true }), { status: 200, headers });
  } catch (err) {
    return new Response(
      JSON.stringify({ success: false, message: "Could not send note right now. Please try emailing marvin@osmoticpoet.com." }),
      { status: 500, headers }
    );
  }
}
