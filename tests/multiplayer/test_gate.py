"""Máy trạng thái xác thực: sai secret, replay, host câm, byte không phải Minecraft — đều rớt."""

from __future__ import annotations

from nostalgia.multiplayer import handshake
from nostalgia.multiplayer.gate import GateStep, HostGate, JoinerGate

MC_HANDSHAKE = bytes([0x10, 0x00, 0xFB, 0x05, 0x09]) + b"localhost" + b"\x63\xdd\x02"


def run_pair(
    host_secret: str, joiner_secret: str, first_bytes: bytes = MC_HANDSHAKE
) -> tuple[GateStep, GateStep | None]:
    host, joiner = HostGate(host_secret), JoinerGate(joiner_secret)
    challenge = host.feed(joiner.hello())
    assert challenge.verdict == "pending" and challenge.reply
    joined = joiner.feed(challenge.reply)
    if joined.verdict != "accepted":
        return joined, None
    return joined, host.feed(joined.reply + first_bytes)


def test_matching_secret_accepts_and_forwards_minecraft_bytes() -> None:
    joined, hosted = run_pair("SECRET", "SECRET")
    assert joined.verdict == "accepted" and hosted is not None
    assert (hosted.verdict, hosted.forward) == ("accepted", MC_HANDSHAKE)


def test_handshake_rejects_wrong_secret_on_both_sides() -> None:
    joined, _ = run_pair("SECRET", "WRONG")  # joiner thấy host_proof sai → tự bỏ
    assert joined.verdict == "rejected"
    host = HostGate("SECRET")
    joiner = JoinerGate("SECRET")
    challenge = host.feed(joiner.hello())
    frame = handshake.parse_frame(challenge.reply)
    assert frame is not None
    forged = handshake.build_response("WRONG", frame.fields[0])
    assert host.feed(forged + MC_HANDSHAKE).verdict == "rejected"


def test_handshake_rejects_replay() -> None:
    joiner = JoinerGate("SECRET")
    first_host = HostGate("SECRET")
    response = joiner.feed(first_host.feed(joiner.hello()).reply).reply
    second_host = HostGate("SECRET")
    second_host.feed(joiner.hello())  # nonce host mới → proof cũ vô giá trị
    assert second_host.feed(response + MC_HANDSHAKE).verdict == "rejected"


def test_joiner_gives_up_when_host_is_silent_or_speaks_garbage() -> None:
    joiner = JoinerGate("SECRET")
    assert joiner.feed(b"NLh1\x06SECRET").verdict == "rejected"  # bản cũ đòi bearer-token
    joiner = JoinerGate("SECRET")
    assert joiner.feed(b"\x00" * 600).verdict == "rejected"  # quá cỡ
    joiner = JoinerGate("SECRET")
    assert joiner.feed(b"NL").verdict == "pending"  # chưa đủ: chờ, nhưng KHÔNG gửi gì


def test_first_bytes_must_be_minecraft_handshake() -> None:
    _, hosted = run_pair("SECRET", "SECRET", first_bytes=b"GET / HTTP/1.1\r\n")
    assert hosted is not None and hosted.verdict == "rejected"
    _, hosted = run_pair("SECRET", "SECRET", first_bytes=b"")
    assert hosted is not None and hosted.verdict == "pending"


def test_hello_must_come_first_and_only_once() -> None:
    host = HostGate("SECRET")
    assert host.feed(handshake.build_response("SECRET", b"x" * 18)).verdict == "rejected"
    host = HostGate("SECRET")
    host.feed(handshake.build_hello(b"n" * 18))
    assert host.feed(handshake.build_hello(b"n" * 18)).verdict == "rejected"


def test_large_first_chunk_after_auth_is_forwarded_whole() -> None:
    big = MC_HANDSHAKE + b"\x00" * 65536  # handshake + phần đầu gói tiếp theo trong cùng chunk
    _, hosted = run_pair("SECRET", "SECRET", first_bytes=big)
    assert hosted is not None and (hosted.verdict, len(hosted.forward)) == ("accepted", len(big))
