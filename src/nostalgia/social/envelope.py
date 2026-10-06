"""Mã phòng mã hóa tới khóa X25519 của máy nhận; dịch vụ bạn bè chỉ giữ ciphertext."""

from __future__ import annotations

import importlib
import secrets

from nostalgia.errors import SocialError
from nostalgia.model.json_value import JsonValue, as_mapping, as_string


class InvitationCipher:
    """Khóa máy hiện hành chỉ ở RAM. Khởi động lại thay khóa và hủy lời mời cũ."""

    def __init__(self) -> None:
        self._x25519 = importlib.import_module("cryptography.hazmat.primitives.asymmetric.x25519")
        self._aes = importlib.import_module("cryptography.hazmat.primitives.ciphers.aead")
        self._hkdf = importlib.import_module("cryptography.hazmat.primitives.kdf.hkdf")
        self._hashes = importlib.import_module("cryptography.hazmat.primitives.hashes")
        self._private = self._x25519.X25519PrivateKey.generate()
        self.public_key: str = self._private.public_key().public_bytes_raw().hex()

    def encrypt(self, room_code: str, target: str, recipient_key: str) -> JsonValue:
        try:
            ephemeral = self._x25519.X25519PrivateKey.generate()
            shared = ephemeral.exchange(
                self._x25519.X25519PublicKey.from_public_bytes(bytes.fromhex(recipient_key))
            )
            nonce = secrets.token_bytes(12)
            room_id = room_code[:6]
            payload = self._aes.AESGCM(self._derive(shared)).encrypt(
                nonce, room_code.encode(), self._aad(room_id, target, recipient_key)
            )
            return {
                "ephemeral_key": ephemeral.public_key().public_bytes_raw().hex(),
                "nonce": nonce.hex(),
                "ciphertext": payload.hex(),
            }
        except (ValueError, TypeError) as exc:
            raise SocialError(
                "Khóa lời mời của bạn không hợp lệ. Hãy nhờ bạn mở lại launcher."
            ) from exc

    def decrypt(self, document: JsonValue, account_id: str) -> str:
        fields = as_mapping(document)
        envelope = as_mapping(fields.get("envelope"))
        room_id = as_string(fields.get("room_id")) or ""
        recipient_key = as_string(fields.get("recipient_key")) or ""
        if recipient_key != self.public_key:
            raise SocialError("Lời mời dành cho phiên cũ. Hãy nhờ bạn gửi lại.")
        try:
            shared = self._private.exchange(
                self._x25519.X25519PublicKey.from_public_bytes(
                    bytes.fromhex(as_string(envelope.get("ephemeral_key")) or "")
                )
            )
            code: bytes = self._aes.AESGCM(self._derive(shared)).decrypt(
                bytes.fromhex(as_string(envelope.get("nonce")) or ""),
                bytes.fromhex(as_string(envelope.get("ciphertext")) or ""),
                self._aad(room_id, account_id, recipient_key),
            )
            room_code = code.decode("ascii")
        except Exception as exc:
            raise SocialError("Không xác minh được lời mời. Hãy nhờ bạn gửi lại.") from exc
        if not room_code.startswith(room_id) or len(room_id) != 6:
            raise SocialError("Lời mời không khớp phòng.")
        return room_code

    def _derive(self, shared: bytes) -> bytes:
        derived: bytes = self._hkdf.HKDF(
            algorithm=self._hashes.SHA256(), length=32, salt=None, info=b"nostalgia-room-invite-v1"
        ).derive(shared)
        return derived

    def _aad(self, room_id: str, account_id: str, recipient_key: str) -> bytes:
        return (room_id + ":" + account_id + ":" + recipient_key).encode()
