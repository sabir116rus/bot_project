# metrics.py

from utils import db_cursor


def get_bot_statistics():
    """Return total number of users and users registered in the last 24 hours."""
    with db_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE datetime(created_at) >= datetime('now', '-1 day')"
        )
        new_users = cursor.fetchone()[0]

    return total_users, new_users
