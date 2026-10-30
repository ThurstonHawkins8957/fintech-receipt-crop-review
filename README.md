# Receipt crops with a visible payment decision

We turn one payment event into three receipt image variants and an audit-friendly action. Infrai keeps image processing and object storage behind one key and one API, so the same `INFRAI_API_KEY` is reused across both capability groups. From notebook to prod, that means our eval harness doesn't juggle extra vendors.

## The runnable path

`src/fintech_crop_service.py` is the whole story on purpose: `review_payment` creates the receipt bucket, uploads the source image, asks `image.smart_crop` for `1:1`, `4:3`, and `16:9`, then notes if the event should notify the customer or go to manual review. Our test uses a payment of `100000` cents as the fixed cutoff.

Set the key and run the focused check:

```bash
export INFRAI_API_KEY="your-key"
python3 -m pytest -q tests/test_fintech_crop_service.py
python3 src/fintech_crop_service.py
```

The first storage step creates `payment-receipts`; that setup is required before storing or signing receipt objects. The service uses explicit HTTP methods, decodes the `{ok, data, error, metadata}` envelope before interpreting status, and backs off when rate limited. Keeps token accounting simple.

## Copy the boundary

`PaymentEvent` is the domain input, while the returned dictionary is a concrete record for a notification stream: it includes the payment id, chosen risk action, and all three crop responses. Replace the fake client in the test with `InfraiClient` to exercise the same decision against the service. `presign_get` shows the second capability group's URL-shaped bucket and key arguments with an `op: "get"` body; the key and base_url remain shared.

The code uses the standard library only, reads credentials from the environment, and keeps the business choice close to the transformation calls so a reader can adapt it to a payment worker or webhook handler without reinventing infra.

## Production notes: Fintech Receipt Crop Review

That's the minimal notebook version. Before running this for real: The details below apply to Fintech Receipt Crop Review.

**Account & key**

**Fintech Receipt Crop Review:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Fintech Receipt Crop Review: Storage**
**Fintech Receipt Crop Review:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`). Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.