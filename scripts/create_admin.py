"""Create an administrator, or promote an existing account to administrator.

Admins cannot be created from the web: POST /api/auth/register always makes a "user" (it has no role field), and
POST /api/admin/users needs a token that is already admin. This script is the way to make the first admin. It talks
to MongoDB directly, so only someone with access to the server (or the Docker host) can run it.

    python scripts/create_admin.py --username admin --email admin@medsignal.local            # asks the password
    python scripts/create_admin.py --promote marlon024                                       # existing account

On the Docker cluster (the API container has the database settings; -it lets it ask for the password):

    docker compose -f deploy/docker-compose.local.yml exec -it api python scripts/create_admin.py --username admin --email admin@medsignal.local

The password can also come from MEDSIGNAL_ADMIN_PASSWORD (for automated setups); it is never a command-line argument,
so it does not end up in the shell history. A new token is needed after a promotion: log out and in again.
"""
import argparse
import asyncio
import getpass
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.security import hash_password
from app.domain.entities.enums import Role
from app.domain.entities.user import User
from app.infrastructure.database_container import build_database_container

MIN_PASSWORD = 8


def ask_password() -> str:
    pw = os.environ.get("MEDSIGNAL_ADMIN_PASSWORD")
    if pw is None:
        pw = getpass.getpass("Password for the new admin: ")
        if pw != getpass.getpass("Repeat it: "):
            sys.exit("The passwords do not match.")
    if len(pw) < MIN_PASSWORD:
        sys.exit(f"The password needs at least {MIN_PASSWORD} characters.")
    return pw


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--username", help="new admin's username (3-32 characters)")
    ap.add_argument("--email", help="new admin's email")
    ap.add_argument("--promote", metavar="USERNAME_OR_EMAIL", help="make an existing account admin")
    args = ap.parse_args()
    settings = get_settings()
    if settings.storage_backend != "databases":
        sys.exit("STORAGE_BACKEND must be 'databases': in memory mode accounts are lost on every restart.")
    c = await build_database_container(settings)

    if args.promote:
        user = await c.users.get_by_username_or_email(args.promote)
        if user is None:
            sys.exit(f"No account '{args.promote}'.")
        if user.role is Role.ADMIN:
            print(f"{user.username} is already admin.")
            return
        await c.users.update(user.model_copy(update={"role": Role.ADMIN}))
        print(f"{user.username} is now admin (log in again to get an admin token).")
        return

    if not (args.username and args.email):
        ap.error("give --username and --email, or --promote")
    if not 3 <= len(args.username) <= 32:
        sys.exit("The username needs 3 to 32 characters.")
    for value in (args.username, args.email):
        if await c.users.get_by_username_or_email(value):
            sys.exit(f"'{value}' is already registered; use --promote {value}.")
    await c.users.create(User(user_id=str(uuid.uuid4()), username=args.username, email=args.email.lower(),
                              password_hash=hash_password(ask_password()), role=Role.ADMIN,
                              created_at=c.clock.now()))
    print(f"Admin {args.username} created. Log in with it to use /api/admin.")


if __name__ == "__main__":
    asyncio.run(main())
