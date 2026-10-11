"""Đăng nhập qua HTTPS thật: chứng chỉ lỗi phải chặn mật khẩu trước request HTTP."""

from __future__ import annotations

import json
import ssl
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.auth.ely import sign_in_ely
from nostalgia.auth.endpoints import DEFAULT_AUTH_ENDPOINTS
from nostalgia.errors import NetworkError
from nostalgia.net.http import HttpClient
from nostalgia.net.tls_failure import certificate_failure


def certificate(directory: Path, fault: str) -> tuple[Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    current = datetime.now(UTC)
    before = current + timedelta(days=1) if fault == "future" else current - timedelta(days=2)
    after = current - timedelta(days=1) if fault == "expired" else current + timedelta(days=2)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    signed = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(before)
        .not_valid_after(after)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), critical=False
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("wrong.example" if fault == "hostname" else "localhost")]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    public, private = directory / "public.pem", directory / "private.pem"
    public.write_bytes(signed.public_bytes(serialization.Encoding.PEM))
    private.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return public, private


@pytest.mark.parametrize("fault", ["expired", "future", "hostname", "untrusted"])
def test_invalid_tls_blocks_ely_credentials_before_any_http_request(
    tmp_path: Path, certificate_pair: tuple[Path, Path], fault: str
) -> None:
    public, private = certificate(tmp_path, fault)
    trusted = certificate_pair[0] if fault == "untrusted" else public
    context = ssl.create_default_context(cafile=str(trusted))
    context.verify_flags |= ssl.VERIFY_X509_STRICT
    state = ServerState()
    path = state.add("/auth/authenticate", b"{}")
    with (
        LocalHttpsServer(state, public, private) as server,
        HttpClient(tls_context=context) as http_client,
    ):
        endpoints = replace(DEFAULT_AUTH_ENDPOINTS, ely_auth_url=server.url("/auth"))
        with pytest.raises(NetworkError, match="chứng chỉ HTTPS") as caught:
            sign_in_ely(
                http_client, "user@example.test", "password-must-not-be-sent", endpoints=endpoints
            )
        assert isinstance(caught.value.__cause__, ssl.SSLCertVerificationError)
        assert "password-must-not-be-sent" not in str(caught.value)
        assert state.request_count(path) == 0
        assert state.received_body(path) == b""
        assert http_client._connections == []
        assert http_client._tls_context is context
        assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
        if fault in ("expired", "future"):
            assert "hết hạn hoặc chưa có hiệu lực" in str(caught.value)
        else:
            assert "hết hạn" not in str(caught.value)


def test_valid_tls_still_authenticates_ely_and_preserves_credentials(tmp_path: Path) -> None:
    public, private = certificate(tmp_path, "valid")
    context = ssl.create_default_context(cafile=str(public))
    context.verify_flags |= ssl.VERIFY_X509_STRICT
    state = ServerState()
    path = state.add(
        "/auth/authenticate",
        json.dumps(
            {
                "accessToken": "valid-test-token",
                "selectedProfile": {"name": "Jun", "id": "a" * 32},
            }
        ).encode(),
    )
    with (
        LocalHttpsServer(state, public, private) as server,
        HttpClient(tls_context=context) as http_client,
    ):
        endpoints = replace(DEFAULT_AUTH_ENDPOINTS, ely_auth_url=server.url("/auth"))
        login = sign_in_ely(http_client, "user@example.test", "password", endpoints=endpoints)
        assert login.player_name == "Jun" and login.access_token == "valid-test-token"
        assert json.loads(state.received_body(path))["password"] == "password"


@pytest.mark.parametrize("code", [0x800B0101, -2146762495, 9, 10])
def test_windows_and_openssl_date_errors_keep_diagnostics_without_raw_ui_text(
    caplog: pytest.LogCaptureFixture, code: int
) -> None:
    error = ssl.SSLCertVerificationError("A required certificate is not within its validity period")
    error.verify_code = code
    error.verify_message = "A required certificate is not within its validity period"
    failure = certificate_failure("authserver.ely.by", error)
    assert "authserver.ely.by" in str(failure)
    assert "hết hạn hoặc chưa có hiệu lực" in str(failure)
    assert "A required certificate" not in str(failure)
    assert "A required certificate" in caplog.text and str(code) in caplog.text
