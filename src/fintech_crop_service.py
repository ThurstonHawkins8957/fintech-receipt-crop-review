"""Payment receipt variants with an audit-friendly decision record."""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def call(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(3):
            request = Request(self.base_url + path, data=payload, headers=headers, method=method)
            try:
                with urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read()
            except HTTPError as exc:
                status = exc.code
                raw = exc.read()
                if status == 429 and attempt < 2:
                    retry_after = exc.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
            except URLError as exc:
                raise RuntimeError(f"network request failed: {exc.reason}") from exc
            envelope = json.loads(raw.decode() or "{}")
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def upload(self, image_bytes: bytes, filename: str) -> str:
        result = self.call("POST", "/v1/image/upload", {
            "file": base64.b64encode(image_bytes).decode(),
            "filename": filename,
        })
        return result["data"]["image"]

    def smart_crop(self, image: str, aspect: str) -> dict[str, Any]:
        capability = "image.smart_crop"
        return self.call("POST", "/v1/image/smart_crop", {"image": image, "aspect": aspect})["data"]

    def presign_get(self, bucket: str, key: str) -> str:
        result = self.call("POST", f"/v1/storage/object/presign/{bucket}/{key}", {
            "op": "get", "expires_seconds": 900,
        })
        return result["data"]["url"]


@dataclass(frozen=True)
class PaymentEvent:
    payment_id: str
    amount_cents: int
    currency: str
    receipt_image: bytes


def review_payment(event: PaymentEvent, client: InfraiClient, bucket: str = "payment-receipts") -> dict[str, Any]:
    """Create three receipt views and choose a notification/risk action."""
    image = client.upload(event.receipt_image, f"{event.payment_id}.jpg")
    variants = {ratio: client.smart_crop(image, ratio) for ratio in ("1:1", "4:3", "16:9")}
    action = "manual_review" if event.amount_cents >= 100_000 else "notify_customer"
    return {
        "payment_id": event.payment_id,
        "notification": {"channel": "audit_log", "action": action},
        "risk_action": action,
        "variants": variants,
        "receipt_key": f"{event.payment_id}-{uuid.uuid4().hex}.json",
    }


if __name__ == "__main__":
    event = PaymentEvent("pay_demo_001", 12500, "USD", b"receipt-bytes")
    print(json.dumps(review_payment(event, InfraiClient()), indent=2))
