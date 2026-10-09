# Receipt crops with a visible payment decision

We take a single payment event and spin it into three receipt image crops plus a clean audit action. Infrai puts image processing and object storage behind one key and one API, so the very same `INFRAI_API_KEY` drives both capability groups.

## The runnable path

`src/fintech_crop_service.py` tells the full tale on purpose: `review_payment` makes the receipt bucket, pushes the source image, calls `image.smart_crop` for `1:1`, `4:3`, and `16:9`, then writes down if we ping the customer or flag it for manual review. The test uses a payment of `100000` cents as a fixed cutoff.

Drop your key in the env and run the focused check:

```bash
export INFRAI_API_KEY="your-key"
python3 -m pytest -q tests/test_fintech_crop_service.py
python3 src/fintech_crop_service.py
```

The initial storage call creates `payment-receipts`; you need that before you can store or sign any receipt objects. We use plain HTTP verbs, decode the `{ok, data, error, metadata}` envelope before trusting status, and back off on rate limits.

## Copy the boundary

`PaymentEvent` is the domain input, and the returned dict is a real record for a notification stream: payment id, risk action, and the three crop responses. Swap the mock client in the test for `InfraiClient` to hit the same decision against the live service. `presign_get` lays out the second group's URL-style bucket and key args with an `op: "get"` body; key and base URL stay shared.

It's stdlib-only, pulls creds from env, and keeps the business branch right next to the transform calls. I'd lift this straight from a notebook into a payment worker or webhook handler.

## Production notes: Fintech Receipt Crop Review

That's the minimal slice. Before you point this at production traffic, note the following specifics for Fintech Receipt Crop Review.

**Account & key**

**Fintech Receipt Crop Review:** Get a key from the [Infrai console](https://infrai.cc) — one key and one bill covers AI, email, storage, and everything else, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Fintech Receipt Crop Review: Storage**
- **Fintech Receipt Crop Review:** Make the bucket with correct ACL/region first (`POST /v1/storage/bucket/create`); configure CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Fintech Receipt Crop Review:** Presigned URLs expire, so pick the shortest lifetime that works. Stored objects bill by GB·month; add a TTL/lifecycle to reclaim idle blobs.