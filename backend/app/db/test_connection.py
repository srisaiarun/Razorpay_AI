from sqlalchemy import text

from backend.app.db.session import engine


def test_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print(result.scalar())


if __name__ == "__main__":
    test_connection()