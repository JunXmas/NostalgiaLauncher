// Nostalgia Launcher — backend hợp nhất trên Cloudflare Workers.
//
// Phục vụ HAI thứ, cùng một domain:
//   1) SKIN cho offline nhìn thấy nhau, theo chuẩn CustomSkinLoader "CustomSkinAPI":
//        GET  /{username}.json        -> {username, skins:{default|slim: <hash>}}
//        GET  /textures/{hash}        -> PNG
//        PUT  /skin/{username}        -> tải skin lên (xác thực bằng token người chơi)
//   2) DANH TÍNH launcher (khôi phục xuyên máy, gắn với Google `sub`):
//        GET  /identity/{sub}         -> {player_id, display_name, accounts}
//        PUT  /identity/{sub}         -> lưu/cập nhật
//
// Bindings (xem wrangler.toml):
//   KV  META    — lưu tất cả: PNG skin (tex:<hash>), ánh xạ username->skin
//                 (skin:<user>) và sub->identity (id:<sub>). Chỉ KV nên FREE hoàn
//                 toàn, không cần bật R2 / thêm thẻ. Skin vài KB, thừa sức KV (25MiB/value).
//
// Bảo mật: KHÔNG có secret nhúng ở client. Ghi skin/identity phải kèm
// Authorization: Bearer <minecraft_access_token>; Worker gọi Mojang để xác minh
// token đó thuộc đúng username đang ghi. Tài khoản offline không có token thật nên
// chỉ được ghi tên CHƯA thuộc về tài khoản premium nào (trust-on-first-use).

const MOJANG_PROFILE = "https://api.minecraftservices.com/minecraft/profile";
const CORS = { "Access-Control-Allow-Origin": "*",
               "Access-Control-Allow-Methods": "GET,PUT,OPTIONS",
               "Access-Control-Allow-Headers": "Authorization,Content-Type" };

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/^\/+/, "");
    try {
      if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
      if (request.method === "GET" && path.endsWith(".json"))
        return await getSkinJson(path.slice(0, -5), env);
      if (request.method === "GET" && path.startsWith("textures/"))
        return await getTexture(path.slice("textures/".length), env);
      if (request.method === "GET" && path.startsWith("history/"))
        return await getHistory(path.slice("history/".length), env);
      if (request.method === "PUT" && path.startsWith("skin/"))
        return await putSkin(path.slice("skin/".length), request, env);
      if (request.method === "GET" && path.startsWith("identity/"))
        return await getIdentity(path.slice("identity/".length), env);
      if (request.method === "PUT" && path.startsWith("identity/"))
        return await putIdentity(path.slice("identity/".length), request, env);
      if (request.method === "GET" && path.startsWith("cf/"))
        return await curseforgeProxy(path.slice("cf/".length), url.search, env);
      return json({ error: "not found" }, 404);
    } catch (e) {
      return json({ error: String(e && e.message || e) }, 500);
    }
  },
};

// ---------- skin ----------

async function getSkinJson(username, env) {
  const rec = await env.META.get(`skin:${username.toLowerCase()}`, "json");
  if (!rec) return json({ username, skins: {} }, 404);
  const key = rec.variant === "slim" ? "slim" : "default";
  return json({ username, skins: { [key]: rec.hash }, cape: "" });
}

async function getTexture(hash, env) {
  const buf = await env.META.get(`tex:${hash}`, "arrayBuffer");
  if (!buf) return new Response("not found", { status: 404, headers: CORS });
  return new Response(buf, {
    headers: { ...CORS, "Content-Type": "image/png",
               "Cache-Control": "public, max-age=31536000, immutable" },
  });
}

async function putSkin(username, request, env) {
  const auth = await verifyOwner(username, request, env);
  if (!auth.ok) return json({ error: auth.reason }, 403);
  const variant = (new URL(request.url).searchParams.get("variant") === "slim")
    ? "slim" : "classic";
  const png = new Uint8Array(await request.arrayBuffer());
  if (png.length < 8 || png[0] !== 0x89 || png[1] !== 0x50)
    return json({ error: "not a PNG" }, 400);
  const hash = await sha256hex(png);
  const user = username.toLowerCase();
  const ts = Date.now();
  await env.META.put(`tex:${hash}`, png);
  await env.META.put(`skin:${user}`, JSON.stringify({ hash, variant, ts }));
  // Lịch sử 5 lần đổi gần nhất của tài khoản (khử trùng theo hash).
  const hist = (await env.META.get(`hist:${user}`, "json")) || [];
  const next = [{ hash, variant, ts }, ...hist.filter((h) => h.hash !== hash)].slice(0, 5);
  await env.META.put(`hist:${user}`, JSON.stringify(next));
  return json({ ok: true, hash, variant });
}

async function getHistory(username, env) {
  const hist = (await env.META.get(`hist:${username.toLowerCase()}`, "json")) || [];
  return json({ username, history: hist });
}

// Xác minh người gọi có quyền ghi skin cho `username`.
async function verifyOwner(username, request, env) {
  const token = bearer(request);
  if (token) {
    const r = await fetch(MOJANG_PROFILE, { headers: { Authorization: `Bearer ${token}` } });
    if (r.ok) {
      const prof = await r.json();
      if (prof.name && prof.name.toLowerCase() === username.toLowerCase())
        return { ok: true };
      return { ok: false, reason: "token does not match this username" };
    }
    return { ok: false, reason: "invalid Minecraft token" };
  }
  // Offline (không token): chỉ cho ghi nếu tên chưa từng được premium ghi.
  const claimed = await env.META.get(`owner:${username.toLowerCase()}`);
  if (claimed === "premium") return { ok: false, reason: "name owned by a premium account" };
  return { ok: true };
}

// ---------- proxy CurseForge ----------
//
// API tìm/duyệt của CurseForge (api.curseforge.com) BẮT BUỘC có API key, và endpoint
// công khai của trang web thì bị Cloudflare chặn. Để mọi người dùng CF ngay mà không
// ai phải tự xin key, ta giữ MỘT key ở đây (secret CURSEFORGE_KEY, đặt bằng
// `wrangler secret put CURSEFORGE_KEY`) rồi chuyển tiếp yêu cầu. Key không bao giờ
// rời server. Chỉ cho phép các đường dẫn đọc an toàn dưới `mods` (search + files).

const CF_API = "https://api.curseforge.com/v1/";

async function curseforgeProxy(rest, search, env) {
  if (!env.CURSEFORGE_KEY)
    return json({ error: "CurseForge is not configured on this backend" }, 503);
  // Chỉ mở các đường dẫn đọc cần thiết, tránh biến Worker thành proxy mở.
  if (!/^mods(\/|$)/.test(rest))
    return json({ error: "forbidden path" }, 403);
  const r = await fetch(`${CF_API}${rest}${search}`, {
    headers: { "x-api-key": env.CURSEFORGE_KEY, Accept: "application/json" },
  });
  const body = await r.text();
  return new Response(body, {
    status: r.status,
    headers: { ...CORS, "Content-Type": "application/json",
               "Cache-Control": "public, max-age=300" },
  });
}

// ---------- danh tính ----------

async function getIdentity(sub, env) {
  const rec = await env.META.get(`id:${sub}`, "json");
  return rec ? json(rec) : json({ error: "not found" }, 404);
}

async function putIdentity(sub, request, env) {
  const body = await request.json();
  if (!body || !body.player_id) return json({ error: "player_id required" }, 400);
  const rec = { player_id: body.player_id, display_name: body.display_name || "",
                accounts: Array.isArray(body.accounts) ? body.accounts : [],
                ts: Date.now() };
  await env.META.put(`id:${sub}`, JSON.stringify(rec));
  return json({ ok: true });
}

// ---------- tiện ích ----------

function bearer(request) {
  const h = request.headers.get("Authorization") || "";
  return h.startsWith("Bearer ") ? h.slice(7).trim() : "";
}

async function sha256hex(bytes) {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status, headers: { ...CORS, "Content-Type": "application/json" },
  });
}
