import csv
import os
import random
import re
import sqlite3
import sys

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

CSV_PATH = os.path.join(BASE_DIR, "data", "msforms_30q_17students.csv")
POINTS_PREFIX = "Points - "
TIME_PREFIX = "Time - "
PASSWORD = "Student123!"


def normalize_text(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def get_db_path():
    db_path = os.getenv("PLA_DB")
    if not db_path:
        db_path = os.path.join(BASE_DIR, "pla.db")
    return db_path


def detect_name_field(fieldnames):
    for name in fieldnames:
        if "name" in name.lower():
            return name
    return None


def build_email(name, existing):
    base = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")
    if not base:
        base = "student"
    email = f"{base}@lct.edu"
    counter = 1
    while email in existing:
        email = f"{base}{counter}@lct.edu"
        counter += 1
    existing.add(email)
    return email


def main():
    if not os.path.exists(CSV_PATH):
        print(f"CSV file not found at {CSV_PATH}")
        return
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    ensure_columns(conn)
    ensure_question_bank(conn)
    seed_lecturer(conn)

    cur = conn.execute("SELECT COUNT(*) AS cnt FROM quiz")
    count = cur.fetchone()["cnt"]
    if count != 30:
        print("Error: Question bank must have exactly 30 questions before seeding.")
        conn.close()
        return

    with open(CSV_PATH, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        points_columns = [name for name in fieldnames if name.startswith(POINTS_PREFIX)]
        if len(points_columns) != 30:
            print(f"Error: Expected 30 'Points - ' columns, found {len(points_columns)}")
            return
        question_texts = [name[len(POINTS_PREFIX):].strip() for name in points_columns]

        cur = conn.execute("SELECT quiz_id, question FROM quiz")
        question_map = {
            normalize_text(row["question"]): row["quiz_id"] for row in cur.fetchall()
        }

        missing = []
        normalized_questions = []
        for text in question_texts:
            norm = normalize_text(text)
            normalized_questions.append((text, norm))
            if norm not in question_map:
                missing.append(text)
        if missing:
            print("Unable to match the following questions from CSV to the database:")
            for text in missing:
                print(f" - {text}")
            print("Aborting without inserting any data.")
            return

        time_columns = {}
        for name in fieldnames:
            if name.startswith(TIME_PREFIX):
                source_text = name[len(TIME_PREFIX):].strip()
                norm = normalize_text(source_text)
                time_columns[norm] = name

        name_field = detect_name_field(fieldnames)
        if not name_field:
            print("Error: Could not find a name column in the CSV.")
            return

        rows = list(reader)

    existing_emails = {
        row["email"].lower()
        for row in conn.execute("SELECT email FROM student")
    }

    password_hash = generate_password_hash(PASSWORD)
    created_credentials = []

    for row in rows:
        name = (row.get(name_field) or "").strip()
        if not name:
            continue
        email = build_email(name, existing_emails)
        conn.execute(
            "INSERT INTO student (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        student_id = conn.execute(
            "SELECT student_id FROM student WHERE email = ?",
            (email,),
        ).fetchone()["student_id"]

        now = format_dt(get_time_now())
        cur = conn.execute(
            "INSERT INTO attempt (student_id, nf_scope, started_at, finished_at, items_total, items_correct, score_pct, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (student_id, "full-quiz", now, now, 30, 0, 0.0, "live"),
        )
        attempt_id = cur.lastrowid

        total_correct = 0
        responses = []
        for (text, norm), points_col in zip(normalized_questions, points_columns):
            quiz_id = question_map[norm]
            value = row.get(points_col, "").strip()
            score = 1 if value and float(value) >= 1 else 0
            answer = "A" if score == 1 else "B"
            time_col = time_columns.get(norm)
            if time_col:
                try:
                    time_value = float(row.get(time_col, "0").strip() or 0)
                except ValueError:
                    time_value = random.uniform(8, 20)
            else:
                time_value = random.uniform(8, 20)
            total_correct += score
            responses.append((student_id, attempt_id, quiz_id, answer, score, time_value))
        conn.executemany(
            "INSERT INTO response (student_id, attempt_id, quiz_id, answer, score, response_time_s) VALUES (?, ?, ?, ?, ?, ?)",
            responses,
        )
        score_pct = round((total_correct / 30) * 100, 2)
        conn.execute(
            "UPDATE attempt SET items_correct = ?, score_pct = ? WHERE attempt_id = ?",
            (total_correct, score_pct, attempt_id),
        )
        created_credentials.append((name, email))

    conn.commit()

    print("Seeded students and attempts. Credentials:")
    for name, email in created_credentials:
        print(f" - {name} -> {email} ({PASSWORD})")

    conn.close()


if __name__ == "__main__":
    main()
