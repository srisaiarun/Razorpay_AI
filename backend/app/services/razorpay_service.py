from __future__ import annotations

from typing import Any

import razorpay

from backend.app.config.settings import (
    RAZORPAY_KEY_ID,
    RAZORPAY_KEY_SECRET,
)


class RazorpayService:
    def __init__(self) -> None:
        if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
            raise RuntimeError(
                "Razorpay API credentials are not configured."
            )

        self.client = razorpay.Client(
            auth=(
                RAZORPAY_KEY_ID,
                RAZORPAY_KEY_SECRET,
            )
        )

    def fetch_payment(
        self,
        payment_id: str,
    ) -> dict[str, Any]:
        return self.client.payment.fetch(payment_id)

    def fetch_order(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        return self.client.order.fetch(order_id)

    def create_payment_link(
        self,
        amount: int,
        currency: str,
        description: str,
        reference_id: str,
        customer_name: str | None = None,
        customer_email: str | None = None,
        customer_contact: str | None = None,
    ) -> dict[str, Any]:

        payload: dict[str, Any] = {
            "amount": amount,
            "currency": currency,
            "description": description,
            "reference_id": reference_id,
        }

        customer: dict[str, str] = {}

        if customer_name:
            customer["name"] = customer_name

        if customer_email:
            customer["email"] = customer_email

        if customer_contact:
            customer["contact"] = customer_contact

        if customer:
            payload["customer"] = customer

        return self.client.payment_link.create(payload)


razorpay_service = RazorpayService()