import os
import sqlite3

from app.app import BASE_DIR, TOPICS, ensure_schema, ensure_columns, ensure_question_bank


def get_db_path():
    db_path = os.getenv("PLA_DB")
    if not db_path:
        db_path = os.path.join(BASE_DIR, "pla.db")
    return db_path


def main():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    ensure_columns(conn)
    ensure_question_bank(conn)

    placeholders = ",".join("?" for _ in TOPICS)
    query = f"SELECT quiz_id FROM quiz WHERE two_category IS NULL OR two_category = '' OR two_category NOT IN ({placeholders})"
    cur = conn.execute(query, TOPICS)
    quiz_ids = [row["quiz_id"] for row in cur.fetchall()]
    if quiz_ids:
        ids = ",".join("?" for _ in quiz_ids)
        conn.execute(f"DELETE FROM response WHERE quiz_id IN ({ids})", quiz_ids)
        conn.execute(f"DELETE FROM quiz WHERE quiz_id IN ({ids})", quiz_ids)
        conn.commit()
        print(f"Removed {len(quiz_ids)} legacy quiz items and related responses.")
    else:
        print("No legacy quiz items found.")
    cur = conn.execute("SELECT COUNT(*) AS cnt FROM quiz")
    count = cur.fetchone()["cnt"]
    print(f"Question count after cleanup: {count}")
    if count != 30:
        print("Warning: Question bank must be exactly 30")
    conn.close()


if __name__ == "__main__":
    main()
