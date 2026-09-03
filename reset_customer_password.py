from pathlib import Path
from getpass import getpass

from dotenv import load_dotenv

from backend.app.core.security import hash_password
from backend.app.db.session import SessionLocal
from backend.app.models import User


# Load the same .env used by the application.
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=False,
)


def main():
    email = "customer.12590@example.com"

    print("RazorRecover AI - Customer Password Reset")
    print("------------------------------------------")
    print(f"Environment file: {ENV_FILE}")
    print(f".env exists: {ENV_FILE.exists()}")
    print()

    password = getpass(
        "Enter new customer password: "
    )

    if len(password) < 8:
        print("Password must be at least 8 characters.")
        return

    confirm_password = getpass(
        "Confirm new customer password: "
    )

    if password != confirm_password:
        print("Passwords do not match.")
        return

    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        if user is None:
            print("Customer user not found.")
            return

        if user.role != "CUSTOMER":
            print(
                f"User exists but has role: {user.role}"
            )
            return

        if user.customer_id is None:
            print(
                "Customer user has no customer_id."
            )
            return

        user.password_hash = hash_password(password)

        db.commit()

        print()
        print("Customer password updated successfully!")
        print("------------------------------------------")
        print(f"Email: {user.email}")
        print(f"Customer ID: {user.customer_id}")
        print(f"Role: {user.role}")
        print(f"Status: {user.status}")
        print("Password: Stored securely as a hash")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()