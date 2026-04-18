import shutil
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    account_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    root = Path(__file__).resolve().parent
    db_path = root / "ozon_ai.db"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        account = conn.execute(
            "SELECT id, profile_dir FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
    finally:
        conn.close()

    if not account:
        print(f"Account {account_id} was not found.")
        return 1

    profile_dir = Path(account["profile_dir"]) if account["profile_dir"] else None
    if not profile_dir:
        profile_dir = root / "ozon_ai" / "data" / "browser_profiles" / f"account_{account_id}"
    profile_dir = profile_dir.resolve()

    allowed_root = (root / "ozon_ai" / "data" / "browser_profiles").resolve()
    if allowed_root not in profile_dir.parents and profile_dir != allowed_root:
        print(f"Refusing to remove profile outside {allowed_root}: {profile_dir}")
        return 2

    if not profile_dir.exists():
        print(f"Profile already absent: {profile_dir}")
        return 0

    shutil.rmtree(profile_dir)
    print(f"Removed browser profile for account {account_id}: {profile_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
