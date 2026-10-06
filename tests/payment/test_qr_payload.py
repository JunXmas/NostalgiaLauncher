"""QR payOS được vẽ nội bộ và giữ kích thước hợp lệ cho popup."""

import pytest

from nostalgia.errors import PaymentError
from nostalgia.payment.parse import parse_offer, parse_order
from nostalgia.payment.qr_payload import render_payment_qr
from payment_fixture import offer_document, order_document


def test_local_qr_png_dimensions() -> None:
    result = render_payment_qr("000201" + "1234567890" * 25)
    document = order_document()
    document["qr_image"] = result
    assert parse_order(document, parse_offer(offer_document())).qr_image == result


@pytest.mark.parametrize("payload", ["", "https://evil.test", "000201☃", "000201" + "a" * 513])
def test_bad_payload_is_rejected(payload: str) -> None:
    with pytest.raises(PaymentError):
        render_payment_qr(payload)
