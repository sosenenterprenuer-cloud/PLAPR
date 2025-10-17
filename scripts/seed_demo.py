import os
import random
import sqlite3

from werkzeug.security import generate_password_hash

from app.app import (
    BASE_DIR,
    TOPICS,
    ensure_schema,
    ensure_columns,
    ensure_question_bank,
    seed_lecturer,
    format_dt,
    get_time_now,
)


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
    seed_lecturer(conn)

    cur = conn.execute("SELECT quiz_id FROM quiz")
    quiz_ids = [row["quiz_id"] for row in cur.fetchall()]
    if len(quiz_ids) != 30:
        print("Question bank must be exactly 30 before seeding demo data.")
        conn.close()
        return

    student_email = "demo@student.edu"
    student_name = "Demo Student"
    password_hash = generate_password_hash("demo123")

    cur = conn.execute("SELECT student_id FROM student WHERE email = ?", (student_email,))
    row = cur.fetchone()
    if row:
        student_id = row["student_id"]
        print("Demo student already exists.")
    else:
        conn.execute(
            "INSERT INTO student (name, email, password_hash) VALUES (?, ?, ?)",
            (student_name, student_email, password_hash),
        )
        conn.commit()
        student_id = conn.execute(
            "SELECT student_id FROM student WHERE email = ?",
            (student_email,),
        ).fetchone()["student_id"]
        print("Created demo student.")

    now = format_dt(get_time_now())
    cur = conn.execute(
        "INSERT INTO attempt (student_id, nf_scope, started_at, finished_at, items_total, items_correct, score_pct, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (student_id, "full-quiz", now, now, 30, 0, 0.0, "live"),
    )
    attempt_id = cur.lastrowid
    responses = [
        (
            student_id,
            attempt_id,
            quiz_id,
            "B",
            0,
            random.uniform(8, 20),
        )
        for quiz_id in quiz_ids
    ]
    conn.executemany(
        "INSERT INTO response (student_id, attempt_id, quiz_id, answer, score, response_time_s) VALUES (?, ?, ?, ?, ?, ?)",
        responses,
    )
    conn.commit()
    print(f"Seeded demo attempt with ID {attempt_id} and 30 responses.")
    conn.close()


if __name__ == "__main__":
    main()
