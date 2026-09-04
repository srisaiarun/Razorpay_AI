import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv()

secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
if not secret:
    raise RuntimeError("RAZORPAY_WEBHOOK_SECRET is missing from .env")

event_id = f"evt_test_{uuid.uuid4().hex}"
payment_id = f"pay_test_{uuid.uuid4().hex}"
order_id = f"order_test_{uuid.uuid4().hex}"

payload = {
    "entity": "event",
    "account_id": "acc_test",
    "event": "payment.failed",
    "contains": ["payment"],
    "payload": {
        "payment": {
            "entity": {
                "id": payment_id,
                "amount": 12345,
                "currency": "INR",
                "status": "failed",
                "method": "card",
                "order_id": order_id,
                "notes": {
                    "customer_id": "1"
                },
                "error_code": "BAD_REQUEST_ERROR",
                "error_description": "Test payment failure"
            }
        }
    },
    "created_at": int(datetime.now(timezone.utc).timestamp())
}

raw_body = json.dumps(
    payload,
    separators=(",", ":")
).encode("utf-8")

signature = hmac.new(
    secret.encode("utf-8"),
    raw_body,
    hashlib.sha256
).hexdigest()

request = Request(
    "http://127.0.0.1:8000/api/v1/webhooks/razorpay",
    data=raw_body,
    headers={
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
    },
    method="POST",
)

try:
    with urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8")
        print(f"HTTP {response.status}")
        print(body)

except Exception as exc:
    print("WEBHOOK TEST FAILED")
    print(exc)