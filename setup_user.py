"""
One-time setup: create or update a user account.
Run with: python setup_user.py
Safe to re-run to change credentials.
"""
import getpass
import json
import os
import sys

# Load .env so DATA_DIR is respected
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # will use defaults

DATA_DIR = os.environ.get("DATA_DIR", "data")
HTPASSWD = os.path.join(DATA_DIR, ".htpasswd.json")

def main():
    try:
        import bcrypt
    except ImportError:
        print("ERROR: bcrypt not installed. Run: pip install bcrypt")
        sys.exit(1)

    os.makedirs(DATA_DIR, exist_ok=True)

    users: dict = {}
    if os.path.exists(HTPASSWD):
        with open(HTPASSWD) as f:
            users = json.load(f)
        print(f"Existing users: {list(users.keys())}")

    username = input("Username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    password = getpass.getpass("Password: ")
    confirm  = getpass.getpass("Confirm password: ")

    if password != confirm:
        print("Passwords do not match.")
        sys.exit(1)

    if len(password) < 4:
        print("Password must be at least 4 characters.")
        sys.exit(1)

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
    users[username] = hashed

    with open(HTPASSWD, "w") as f:
        json.dump(users, f, indent=2)

    os.chmod(HTPASSWD, 0o600)
    print(f"\n✅ User '{username}' saved to {HTPASSWD}")
    print("Start the server with: python run.py")

if __name__ == "__main__":
    main()
