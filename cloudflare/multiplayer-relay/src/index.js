// Nostalgia multiplayer relay — Cloudflare Worker + Durable Object.
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
      if (this.host) this.host.close(4001, "host already connected");
      this.host = server;
      server.addEventListener("message", (e) => this.fromHost(e.data));
      const teardown = () => {
        this.host = null;
        for (const j of this.joiners.values()) try { j.close(1001, "host left"); } catch {}
        this.joiners.clear();
      };
      server.addEventListener("close", teardown);
      server.addEventListener("error", teardown);
    } else if (role === "join") {
      if (!this.host) { server.close(4004, "no host"); return new Response(null, { status: 101, webSocket: client }); }
      const id = this.nextId++;
      this.joiners.set(id, server);
      this.safeHostSend(frame(id, OPEN, null));
      server.addEventListener("message", (e) => this.safeHostSend(frame(id, DATA, e.data)));
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
