import os
import shutil
from datetime import datetime

from app.app import BASE_DIR


def get_db_path():
    db_path = os.getenv("PLA_DB")
    if not db_path:
        db_path = os.path.join(BASE_DIR, "pla.db")
    return db_path


def main():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return
    backup_dir = os.path.join(os.path.dirname(BASE_DIR), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    dest = os.path.join(backup_dir, f"pla_{timestamp}.db")
    shutil.copy2(db_path, dest)
    print(f"Backup created at {dest}")


if __name__ == "__main__":
    main()
