// Proxy ที่สั่งรัน GitHub Actions workflow_dispatch แทนปุ่ม "Refresh ข้อมูล" บนดาชบอร์ด
// เก็บ GitHub token เป็น Worker secret (env.GH_TOKEN) เท่านั้น ไม่ฝังในโค้ดหรือหน้าเว็บ public

const OWNER = "rackoran-netizen";
const REPO = "generate_dashboard";
const WORKFLOW_FILE = "update.yml";
const ALLOWED_ORIGIN = "https://rackoran-netizen.github.io";

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

async function triggerDispatch(env) {
  return fetch(
    `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`,
    {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.GH_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "User-Agent": "jetts-rra-refresh-worker",
      },
      body: JSON.stringify({ ref: "main" }),
    }
  );
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405, headers: corsHeaders() });
    }

    const ghRes = await triggerDispatch(env);

    if (ghRes.status === 204) {
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json", ...corsHeaders() },
      });
    }

    const detail = await ghRes.text();
    return new Response(JSON.stringify({ ok: false, status: ghRes.status, detail }), {
      status: 502,
      headers: { "Content-Type": "application/json", ...corsHeaders() },
    });
  },

  // Cloudflare Cron Trigger — สั่ง workflow_dispatch ตรงเวลาแม่นยำทุกเช้า
  // แทนการพึ่ง GitHub Actions `schedule:` ซึ่งเคยดีเลย์ ~2-3 ชม. (ดู CLAUDE.md)
  async scheduled(event, env, ctx) {
    ctx.waitUntil(triggerDispatch(env));
  },
};
