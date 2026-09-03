from __future__ import annotations

from pathlib import Path
import secrets
import string

from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True,
)


# =========================================================
# IMPORT APPLICATION MODULES
# =========================================================
#
# These imports intentionally happen AFTER .env is loaded.
# =========================================================

from backend.app.db.session import SessionLocal
from backend.app.models.customer import Customer


# =========================================================
# CONFIGURATION
# =========================================================

ACCESS_ID_PREFIX = "CUST-"

# Uppercase letters + numbers.
# We intentionally exclude ambiguous characters:
# 0, O, 1, I
#
# This makes IDs easier for humans to read and type.
ACCESS_ID_ALPHABET = (
    "23456789"
    "ABCDEFGHJKLMNPQRSTUVWXYZ"
)

ACCESS_ID_LENGTH = 6


# =========================================================
# ACCESS ID GENERATION
# =========================================================

def generate_access_id() -> str:
    """
    Generate a cryptographically secure customer access ID.

    Example:
        CUST-7K4M2P
    """

    random_part = "".join(
        secrets.choice(ACCESS_ID_ALPHABET)
        for _ in range(ACCESS_ID_LENGTH)
    )

    return f"{ACCESS_ID_PREFIX}{random_part}"


# =========================================================
# MAIN
# =========================================================

def main():
    print()
    print("=" * 60)
    print("RazorRecover AI - Customer Access ID Generator")
    print("=" * 60)

    print(f"Environment file: {ENV_FILE}")
    print(f".env exists: {ENV_FILE.exists()}")

    if not ENV_FILE.exists():
        print()
        print("ERROR: .env file was not found.")
        return

    db = SessionLocal()

    try:
        # -------------------------------------------------
        # Get all customers
        # -------------------------------------------------

        customers = (
            db.query(Customer)
            .order_by(Customer.id.asc())
            .all()
        )

        total_customers = len(customers)

        print()
        print(f"Total customers found: {total_customers}")

        if total_customers == 0:
            print()
            print("No customers found in the database.")
            return

        # -------------------------------------------------
        # Track statistics
        # -------------------------------------------------

        already_had_access_id = 0
        generated_count = 0

        generated_ids: set[str] = set()

        # -------------------------------------------------
        # Generate IDs
        # -------------------------------------------------

        for customer in customers:

            # Never overwrite an existing access ID.
            if customer.customer_access_id:
                already_had_access_id += 1
                continue

            # Generate a unique ID.
            while True:
                access_id = generate_access_id()

                # Check IDs generated during this run.
                if access_id in generated_ids:
                    continue

                # Check IDs already stored in the database.
                existing_customer = (
                    db.query(Customer)
                    .filter(
                        Customer.customer_access_id
                        == access_id
                    )
                    .first()
                )

                if existing_customer is not None:
                    continue

                break

            # Assign the new ID.
            customer.customer_access_id = access_id

            generated_ids.add(access_id)
            generated_count += 1

            print(
                f"Customer {customer.id:<5} "
                f"-> {customer.customer_access_id}"
            )

        # -------------------------------------------------
        # Save changes
        # -------------------------------------------------

        db.commit()

        # -------------------------------------------------
        # Verify
        # -------------------------------------------------

        customers_after = (
            db.query(Customer)
            .order_by(Customer.id.asc())
            .all()
        )

        customers_without_access_id = [
            customer
            for customer in customers_after
            if not customer.customer_access_id
        ]

        all_access_ids = [
            customer.customer_access_id
            for customer in customers_after
            if customer.customer_access_id
        ]

        unique_access_ids = set(all_access_ids)

        # -------------------------------------------------
        # Final report
        # -------------------------------------------------

        print()
        print("=" * 60)
        print("GENERATION COMPLETE")
        print("=" * 60)

        print(
            f"Total customers:          "
            f"{len(customers_after)}"
        )

        print(
            f"Already had access ID:    "
            f"{already_had_access_id}"
        )

        print(
            f"New access IDs generated: "
            f"{generated_count}"
        )

        print(
            f"Customers without ID:     "
            f"{len(customers_without_access_id)}"
        )

        print(
            f"Unique access IDs:        "
            f"{len(unique_access_ids)}"
        )

        print(
            f"Total stored access IDs:  "
            f"{len(all_access_ids)}"
        )

        # -------------------------------------------------
        # Safety verification
        # -------------------------------------------------

        if customers_without_access_id:
            print()
            print(
                "WARNING: Some customers do not have "
                "an access ID."
            )

            for customer in customers_without_access_id:
                print(
                    f"  Customer ID: {customer.id}"
                )

            return

        if len(all_access_ids) != len(unique_access_ids):
            print()
            print(
                "ERROR: Duplicate customer access IDs detected!"
            )

            return

        if len(all_access_ids) != len(customers_after):
            print()
            print(
                "ERROR: Access ID count does not match "
                "customer count!"
            )

            return

        print()
        print("SUCCESS")
        print(
            "Every customer has a unique customer "
            "access ID."
        )

        print()
        print("Example access IDs:")

        for customer in customers_after[:10]:
            print(
                f"  Customer {customer.id:<5} "
                f"{customer.customer_access_id}"
            )

        if len(customers_after) > 10:
            print(
                f"  ... and "
                f"{len(customers_after) - 10} more"
            )

        print()
        print("=" * 60)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()