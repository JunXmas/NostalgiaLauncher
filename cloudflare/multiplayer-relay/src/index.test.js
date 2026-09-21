// Test rate-limit của RelaySession (JL-19). Chạy: node --test src/index.test.js
// Chỉ gọi thẳng rateLimited() — không cần WebSocketPair (chỉ có trong runtime workerd).
import { test } from "node:test";
import assert from "node:assert/strict";
import { RelaySession } from "./index.js";

const RL_WINDOW_MS = 10_000;
const RL_MAX = 30;

test("duoi RL_MAX lan noi trong cua so thi khong bi chan", () => {
  const s = new RelaySession(null);
  let now = 0;
  for (let i = 0; i < RL_MAX; i++) {
    assert.equal(s.rateLimited(now), false, `lan noi thu ${i + 1} khong duoc chan`);
    now += 1;
  }
});

test("lan noi thu RL_MAX+1 trong cung cua so bi chan", () => {
  const s = new RelaySession(null);
  let now = 0;
  for (let i = 0; i < RL_MAX; i++) s.rateLimited(now++);
  assert.equal(s.rateLimited(now), true, "vuot RL_MAX phai bi chan");
});

test("qua cua so RL_WINDOW_MS thi mốc cu bi rot, duoc noi lai", () => {
  const s = new RelaySession(null);
  let now = 0;
  for (let i = 0; i < RL_MAX; i++) s.rateLimited(now++);
  assert.equal(s.rateLimited(now), true, "van trong cua so -> con bi chan");
  assert.equal(s.rateLimited(now + RL_WINDOW_MS), false, "qua cua so -> het bi chan");
});
