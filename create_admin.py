"""Run once to create the first administrator account, then keep this script private."""
import getpass
import os
import re
import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()
name = input("Administrator full name: ").strip()
email = input("Administrator email: ").strip().lower()
password = getpass.getpass("Choose a strong password (not displayed): ")
confirm = getpass.getpass("Repeat password: ")

if not name or not email or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
    raise SystemExit("Please enter a name and valid email.")
if len(password) < 12 or password != confirm:
    raise SystemExit("Passwords must match and be at least 12 characters.")
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3307")),
    user=os.getenv("DB_USER", "health_app"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "community_health_db"),
)
try:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO workers (full_name, email, password_hash, role) VALUES (%s,%s,%s,'admin')",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    print("Administrator created. You can now log in.")
except mysql.connector.Error as exc:
    conn.rollback()
    raise SystemExit(f"Could not create administrator: {exc}")
finally:
    conn.close()
