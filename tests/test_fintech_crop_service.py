from src.fintech_crop_service import PaymentEvent, review_payment


class FakeClient:
    def create_bucket(self, name):
        return {"name": name}

    def upload(self, image_bytes, filename):
        return "img_receipt"

    def smart_crop(self, image, aspect):
        return {"image": image, "aspect": aspect}


def test_large_payment_is_manual_review_with_all_variants():
    result = review_payment(PaymentEvent("p-7", 100000, "USD", b"x"), FakeClient())
    assert result["risk_action"] == "manual_review"
    assert result["notification"]["action"] == "manual_review"
    assert set(result["variants"]) == {"1:1", "4:3", "16:9"}
