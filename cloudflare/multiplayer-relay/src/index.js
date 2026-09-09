// Nostalgia multiplayer relay — Cloudflare Worker + Durable Object.
// Luật L8 (docs/MULTIPLAYER_SECURITY.md): relay không được tin, chỉ chặn lạm dụng rẻ tiền.
//
// Ghép một máy HOST (mở "Open to LAN") với nhiều JOINER, mỗi bên chỉ kết nối RA
// NGOÀI bằng WebSocket (WSS 443) nên khác mạng / sau NAT vẫn thông, không cần mở
// port hay IP tĩnh. Không đụng gì tới máy người chơi.
//
// Giao thức mux trên MỘT WS của host:  [streamId:4 BE][flag:1][payload...]
//   flag 0 = DATA, 1 = OPEN (joiner mới), 2 = CLOSE.
// Mỗi JOINER là một WS riêng, trao đổi payload THÔ (DO tự bọc/mở khung mux).
//
// Endpoint:  wss://<worker>/s/<sessionId>?role=host   (một máy host)
//            wss://<worker>/s/<sessionId>?role=join   (mỗi người vào)

const DATA = 0, OPEN = 1, CLOSE = 2;

// Chốt chống lạm dụng ở relay (mỗi session = một Durable Object, state trong RAM
// giữ được giữa các request khi DO còn "ấm"). Relay KHÔNG thấy secret room nên
// không tự kiểm được auth; các trần này chặn brute-force / DoS ở tầng kết nối.
const MAX_JOINERS = 16;          // world "Open to LAN" không chịu hơn; trần cũ 64 thừa 4 lần
const RL_WINDOW_MS = 10_000;     // cửa sổ rate-limit cho MỌI lần nối (host lẫn join)
const RL_MAX = 30;               // tối đa RL_MAX lần nối trong RL_WINDOW_MS
const MAX_FRAME_BYTES = 1_048_576; // client đọc chunk 64 KiB nên không bao giờ cần hơn 1 MiB
// Một mã đóng DUY NHẤT cho "phòng trống", "bị rate-limit", "đầy", "slot host đã có chủ":
// trả mã khác nhau là biến relay thành oracle dò room_id (luật L8, docs/MULTIPLAYER_SECURITY.md).
const REFUSED = 4004;

function byteLength(x) { return typeof x === "string" ? x.length : (x && x.byteLength) || 0; }

function frame(id, flag, payload) {
  const head = new Uint8Array(5);
  new DataView(head.buffer).setUint32(0, id >>> 0);
  head[4] = flag;
  const body = payload && payload.byteLength ? new Uint8Array(payload) : new Uint8Array(0);
  const out = new Uint8Array(head.length + body.length);
  out.set(head, 0); out.set(body, head.length);
  return out.buffer;
}

export class RelaySession {
  constructor(state) {
    this.state = state;
    this.host = null;              // host WebSocket (mux)
    this.joiners = new Map();      // streamId -> joiner WebSocket
    this.nextId = 1;
    this.joinTimes = [];           // mốc thời gian các lần nối join (rate-limit)
  }

  async fetch(request) {
    const url = new URL(request.url);
    const role = url.searchParams.get("role");
    if (request.headers.get("Upgrade") !== "websocket")
      return new Response("expected websocket", { status: 426 });

    const pair = new WebSocketPair();
    const client = pair[0], server = pair[1];
    server.accept();

    if (role === "host") {
      // HOST ĐẦU TIÊN GIỮ CHỖ: không cho host sau ĐÁ host cũ. Trước đây host mới
      // đá host cũ -> kẻ biết session (6 ký tự) chiếm slot host, đẩy world/modpack
      // độc. Nay slot đã có chủ thì từ chối kẻ đến sau; host thật rớt (close/error)
      // mới nhả slot. (Joiner vẫn xác thực host bằng HMAC ở tầng app — mutual auth.)
      if (this.host) { server.close(REFUSED, "refused"); return new Response(null, { status: 101, webSocket: client }); }
      this.host = server;
      server.addEventListener("message", (e) => this.fromHost(e.data));
      const teardown = () => {
        if (this.host !== server) return;   // chỉ host đương nhiệm mới được dọn
        this.host = null;
        for (const j of this.joiners.values()) try { j.close(1001, "host left"); } catch {}
        this.joiners.clear();
      };
      server.addEventListener("close", teardown);
      server.addEventListener("error", teardown);
    } else if (role === "join") {
      if (!this.host || this.joiners.size >= MAX_JOINERS) { server.close(REFUSED, "refused"); return new Response(null, { status: 101, webSocket: client }); }
      const id = this.nextId++;
      this.joiners.set(id, server);
      this.safeHostSend(frame(id, OPEN, null));
      server.addEventListener("message", (e) => {
        if (byteLength(e.data) > MAX_FRAME_BYTES) { try { server.close(1009, "frame too big"); } catch {} return; }
        this.safeHostSend(frame(id, DATA, e.data));
      });
      const drop = () => {
        if (this.joiners.delete(id)) this.safeHostSend(frame(id, CLOSE, null));
      };
      server.addEventListener("close", drop);
      server.addEventListener("error", drop);
    } else {
      server.close(4000, "role must be host|join");
    }
    return new Response(null, { status: 101, webSocket: client });
  }

  fromHost(buf) {
    if (byteLength(buf) > MAX_FRAME_BYTES) { try { this.host.close(1009, "frame too big"); } catch {} return; }
    const view = new Uint8Array(buf);
    if (view.byteLength < 5) return;
    const id = new DataView(view.buffer, view.byteOffset, 5).getUint32(0);
    const flag = view[5 - 1];
    const payload = view.subarray(5);
    const j = this.joiners.get(id);
    if (!j) return;
    if (flag === DATA) { try { j.send(payload); } catch {} }
    else if (flag === CLOSE) { this.joiners.delete(id); try { j.close(1000, "stream closed"); } catch {} }
  }

  safeHostSend(buf) { if (this.host) try { this.host.send(buf); } catch {} }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const m = url.pathname.match(/^\/s\/([A-Za-z0-9_-]{1,64})$/);
    if (!m) return new Response("Nostalgia relay", { status: 200 });
    const id = env.RELAY.idFromName(m[1]);
    return env.RELAY.get(id).fetch(request);
  },
};
