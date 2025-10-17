import json
import os
import random
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    flash,
)
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python<3.9 fallback
    ZoneInfo = None

APP_TITLE = "Personalized Learning Recommendation AI"
TOPICS = [
    "Data Modeling & DBMS Fundamentals",
    "Normalization & Dependencies",
]
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.getenv("PLA_SECRET", "pla-dev-secret")

_db_initialized = False


QUESTION_BANK = [
    {
        "question": "What is the primary purpose of a Database Management System (DBMS)?",
        "options": [
            "To store, manage, and retrieve data efficiently",
            "To design hardware for databases",
            "To replace the operating system",
            "To create graphical user interfaces",
        ],
        "correct": "A",
        "topic": TOPICS[0],
        "explanation": "A DBMS provides an efficient way to store, manage, and retrieve data while ensuring integrity and security.",
    },
    {
        "question": "Which term describes a collection of related data organized so information can be easily accessed?",
        "options": [
            "Algorithm",
            "Database",
            "Cache",
            "Filesystem",
        ],
        "correct": "B",
        "topic": TOPICS[0],
        "explanation": "A database is an organized collection of data that enables efficient access and management.",
    },
    {
        "question": "In an ER model, what does an entity represent?",
        "options": [
            "A relationship between tables",
            "A real-world object or concept",
            "A column in a table",
            "A SQL statement",
        ],
        "correct": "B",
        "topic": TOPICS[0],
        "explanation": "Entities correspond to real-world objects or concepts that have data stored about them in a database.",
    },
    {
        "question": "Which key uniquely identifies each row in a table?",
        "options": [
            "Foreign key",
            "Primary key",
            "Composite key",
            "Alternate key",
        ],
        "correct": "B",
        "topic": TOPICS[0],
        "explanation": "The primary key uniquely identifies each row in a table and prevents duplicates.",
    },
    {
        "question": "What does the term 'cardinality' describe in an ER diagram?",
        "options": [
            "Number of attributes in an entity",
            "Number of tables in a schema",
            "The relationship count between entities",
            "The size of a database file",
        ],
        "correct": "C",
        "topic": TOPICS[0],
        "explanation": "Cardinality specifies how many instances of one entity relate to instances of another entity (e.g., one-to-many).",
    },
    {
        "question": "Which SQL statement is used to define or modify the structure of database objects?",
        "options": [
            "DML",
            "DCL",
            "DDL",
            "DQL",
        ],
        "correct": "C",
        "topic": TOPICS[0],
        "explanation": "Data Definition Language (DDL) statements, such as CREATE or ALTER, define or modify database structures.",
    },
    {
        "question": "What is an attribute in the context of a relational database?",
        "options": [
            "A table",
            "A column that describes a property of an entity",
            "A row identifier",
            "A relationship between tables",
        ],
        "correct": "B",
        "topic": TOPICS[0],
        "explanation": "Attributes are the columns of a table that describe the properties of the stored entities.",
    },
    {
        "question": "Which SQL clause filters records returned by a SELECT statement?",
        "options": [
            "GROUP BY",
            "HAVING",
            "WHERE",
            "ORDER BY",
        ],
        "correct": "C",
        "topic": TOPICS[0],
        "explanation": "The WHERE clause specifies conditions that rows must satisfy to be included in the result set.",
    },
    {
        "question": "What does DML stand for in SQL?",
        "options": [
            "Data Modification Language",
            "Data Manipulation Language",
            "Data Modeling Language",
            "Database Management Language",
        ],
        "correct": "B",
        "topic": TOPICS[0],
        "explanation": "Data Manipulation Language (DML) statements such as INSERT, UPDATE, and DELETE modify data within tables.",
    },
    {
        "question": "Which key is used to establish a relationship between two tables?",
        "options": [
            "Candidate key",
            "Foreign key",
            "Super key",
            "Alternate key",
        ],
        "correct": "B",
        "topic": TOPICS[0],
        "explanation": "A foreign key references the primary key of another table to establish relationships between tables.",
    },
    {
        "question": "What is the role of a schema in a database?",
        "options": [
            "It stores table data",
            "It defines the logical structure of the database",
            "It executes SQL queries",
            "It backs up data",
        ],
        "correct": "B",
        "topic": TOPICS[0],
        "explanation": "A schema is the blueprint that outlines the logical structure of database objects, such as tables and relationships.",
    },
    {
        "question": "Which component represents the columns of a table in an ER diagram?",
        "options": [
            "Entities",
            "Attributes",
            "Relationships",
            "Constraints",
        ],
        "correct": "B",
        "topic": TOPICS[0],
        "explanation": "Attributes in an ER diagram map to the columns of tables in the relational model.",
    },
    {
        "question": "Which SQL command retrieves data from a table?",
        "options": [
            "SELECT",
            "INSERT",
            "UPDATE",
            "DELETE",
        ],
        "correct": "A",
        "topic": TOPICS[0],
        "explanation": "The SELECT statement retrieves data from one or more tables in a database.",
    },
    {
        "question": "What is the term for a relationship involving three entities in ER modeling?",
        "options": [
            "Recursive relationship",
            "Unary relationship",
            "Ternary relationship",
            "Binary relationship",
        ],
        "correct": "C",
        "topic": TOPICS[0],
        "explanation": "A ternary relationship links three distinct entities in an ER model.",
    },
    {
        "question": "Which SQL constraint ensures that a column cannot contain NULL values?",
        "options": [
            "DEFAULT",
            "NOT NULL",
            "CHECK",
            "UNIQUE",
        ],
        "correct": "B",
        "topic": TOPICS[0],
        "explanation": "The NOT NULL constraint enforces that a column must always have a value.",
    },
    {
        "question": "What is the goal of normalization in database design?",
        "options": [
            "To maximize redundancy",
            "To minimize data redundancy and anomalies",
            "To improve hardware performance",
            "To enforce data encryption",
        ],
        "correct": "B",
        "topic": TOPICS[1],
        "explanation": "Normalization reduces redundancy and prevents update, insert, and delete anomalies.",
    },
    {
        "question": "What does 1NF require in a relational table?",
        "options": [
            "No partial dependencies",
            "No transitive dependencies",
            "Atomic attribute values",
            "Functional dependencies are preserved",
        ],
        "correct": "C",
        "topic": TOPICS[1],
        "explanation": "First Normal Form (1NF) requires that each column contains atomic, indivisible values.",
    },
    {
        "question": "Which anomaly occurs when deleting a row unintentionally removes other valuable data?",
        "options": [
            "Insertion anomaly",
            "Update anomaly",
            "Deletion anomaly",
            "Modification anomaly",
        ],
        "correct": "C",
        "topic": TOPICS[1],
        "explanation": "A deletion anomaly happens when removing a record causes unintended data loss due to redundancy.",
    },
    {
        "question": "What is a functional dependency?",
        "options": [
            "A relationship between two databases",
            "A constraint between two sets of attributes",
            "A dependency on database hardware",
            "A link between two schemas",
        ],
        "correct": "B",
        "topic": TOPICS[1],
        "explanation": "A functional dependency expresses a constraint where one set of attributes determines another set.",
    },
    {
        "question": "Which normal form removes partial dependencies on a composite primary key?",
        "options": [
            "1NF",
            "2NF",
            "3NF",
            "BCNF",
        ],
        "correct": "B",
        "topic": TOPICS[1],
        "explanation": "Second Normal Form (2NF) removes partial dependencies of non-key attributes on part of a composite key.",
    },
    {
        "question": "Which normal form eliminates transitive dependencies?",
        "options": [
            "1NF",
            "2NF",
            "3NF",
            "BCNF",
        ],
        "correct": "C",
        "topic": TOPICS[1],
        "explanation": "Third Normal Form (3NF) ensures that non-key attributes depend only on the primary key, eliminating transitive dependencies.",
    },
    {
        "question": "What is a determinant in normalization theory?",
        "options": [
            "A primary key candidate",
            "An attribute that determines other attributes",
            "A redundant column",
            "A foreign key",
        ],
        "correct": "B",
        "topic": TOPICS[1],
        "explanation": "A determinant is an attribute on which some other attribute is fully functionally dependent.",
    },
    {
        "question": "BCNF is a stronger version of which normal form?",
        "options": [
            "1NF",
            "2NF",
            "3NF",
            "4NF",
        ],
        "correct": "C",
        "topic": TOPICS[1],
        "explanation": "Boyce-Codd Normal Form (BCNF) is a stronger version of 3NF that requires every determinant to be a candidate key.",
    },
    {
        "question": "What does a lossless decomposition ensure?",
        "options": [
            "The decomposed tables can be joined without losing information",
            "The database size decreases",
            "The schema has fewer tables",
            "The data becomes encrypted",
        ],
        "correct": "A",
        "topic": TOPICS[1],
        "explanation": "A lossless decomposition guarantees that joining the decomposed tables restores the original relation without data loss.",
    },
    {
        "question": "Which dependency type causes update anomalies when data is repeated unnecessarily?",
        "options": [
            "Transitive dependency",
            "Functional dependency",
            "Partial dependency",
            "Temporal dependency",
        ],
        "correct": "C",
        "topic": TOPICS[1],
        "explanation": "Partial dependencies in improperly normalized tables can result in repeated data and update anomalies.",
    },
    {
        "question": "What does the term 'transitive dependency' imply?",
        "options": [
            "Attribute A determines attribute B directly",
            "Attribute A determines attribute C through attribute B",
            "Attributes are independent",
            "Attributes are unrelated",
        ],
        "correct": "B",
        "topic": TOPICS[1],
        "explanation": "A transitive dependency occurs when one attribute depends on another through an intermediate attribute.",
    },
    {
        "question": "Which normal form focuses on eliminating multivalued dependencies?",
        "options": [
            "2NF",
            "3NF",
            "4NF",
            "5NF",
        ],
        "correct": "C",
        "topic": TOPICS[1],
        "explanation": "Fourth Normal Form (4NF) addresses multivalued dependencies to prevent redundant data combinations.",
    },
    {
        "question": "What is the process of splitting a relation into smaller relations to remove anomalies called?",
        "options": [
            "Denormalization",
            "Decomposition",
            "Aggregation",
            "Transformation",
        ],
        "correct": "B",
        "topic": TOPICS[1],
        "explanation": "Decomposition breaks a relation into smaller relations to eliminate redundancy and anomalies.",
    },
    {
        "question": "Which rule ensures that decomposition preserves all functional dependencies?",
        "options": [
            "Dependency preservation",
            "Lossless join",
            "Referential integrity",
            "Domain integrity",
        ],
        "correct": "A",
        "topic": TOPICS[1],
        "explanation": "Dependency preservation ensures that all functional dependencies remain enforceable after decomposition.",
    },
    {
        "question": "Which dependency involves a non-key attribute determining another non-key attribute?",
        "options": [
            "Functional dependency",
            "Partial dependency",
            "Transitive dependency",
            "Referential dependency",
        ],
        "correct": "C",
        "topic": TOPICS[1],
        "explanation": "A transitive dependency exists when a non-key attribute depends on another non-key attribute.",
    },
    {
        "question": "Why is dependency analysis important during normalization?",
        "options": [
            "To design faster hardware",
            "To identify how attributes rely on each other",
            "To encrypt sensitive data",
            "To generate SQL queries automatically",
        ],
        "correct": "B",
        "topic": TOPICS[1],
        "explanation": "Understanding attribute dependencies is essential to eliminate redundancy and maintain data integrity.",
    },
    {
        "question": "Which statement best describes partial dependency?",
        "options": [
            "A non-key attribute depends on part of a composite key",
            "A key attribute depends on another key",
            "An attribute depends on itself",
            "An attribute depends on the entire key",
        ],
        "correct": "A",
        "topic": TOPICS[1],
        "explanation": "A partial dependency occurs when a non-key attribute depends on only part of a composite primary key.",
    },
    {
        "question": "What does normalization primarily protect against?",
        "options": [
            "Security breaches",
            "Data anomalies caused by redundancy",
            "User input errors",
            "Network failures",
        ],
        "correct": "B",
        "topic": TOPICS[1],
        "explanation": "Normalization reduces redundant data, which in turn prevents anomalies during insert, update, or delete operations.",
    },
    {
        "question": "What is the purpose of a dependency diagram?",
        "options": [
            "To visualize functional dependencies",
            "To monitor database performance",
            "To design user interfaces",
            "To control transaction logs",
        ],
        "correct": "A",
        "topic": TOPICS[1],
        "explanation": "Dependency diagrams illustrate functional dependencies and help determine necessary normal forms.",
    },
]


def get_db():
    global _db_initialized
    if "db" not in g:
        db_path = os.getenv("PLA_DB")
        if not db_path:
            db_path = os.path.join(BASE_DIR, "pla.db")
        needs_reset = os.getenv("PLA_RESET") == "1"
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
        if needs_reset:
            reset_database(g.db)
            os.environ.pop("PLA_RESET", None)
        if not _db_initialized or needs_reset:
            ensure_schema(g.db)
            ensure_columns(g.db)
            ensure_question_bank(g.db)
            auto_tag_questions(g.db)
            purge_legacy_content(g.db)
            seed_lecturer(g.db)
            _db_initialized = True
    return g.db


def reset_database(db):
    app.logger.info("Resetting database as requested by PLA_RESET=1")
    db.executescript(
        """
        DROP TABLE IF EXISTS response;
        DROP TABLE IF EXISTS attempt;
        DROP TABLE IF EXISTS feedback;
        DROP TABLE IF EXISTS quiz;
        DROP TABLE IF EXISTS student;
        DROP TABLE IF EXISTS lecturer;
        """
    )
    ensure_schema(db)
    db.commit()


def ensure_schema(db):
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS student (
          student_id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS lecturer (
          lecturer_id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quiz (
          quiz_id INTEGER PRIMARY KEY,
          question TEXT NOT NULL,
          options_text TEXT,
          correct_answer TEXT NOT NULL,
          two_category TEXT,
          explanation TEXT
        );

        CREATE TABLE IF NOT EXISTS attempt (
          attempt_id INTEGER PRIMARY KEY,
          student_id INTEGER NOT NULL,
          nf_scope TEXT,
          started_at TEXT DEFAULT (datetime('now')),
          finished_at TEXT,
          items_total INTEGER DEFAULT 0,
          items_correct INTEGER DEFAULT 0,
          score_pct REAL DEFAULT 0,
          source TEXT DEFAULT 'live',
          FOREIGN KEY(student_id) REFERENCES student(student_id)
        );

        CREATE TABLE IF NOT EXISTS response (
          response_id INTEGER PRIMARY KEY,
          student_id INTEGER NOT NULL,
          attempt_id INTEGER NOT NULL,
          quiz_id INTEGER NOT NULL,
          answer TEXT,
          score INTEGER DEFAULT 0,
          response_time_s REAL DEFAULT 0,
          FOREIGN KEY(student_id) REFERENCES student(student_id),
          FOREIGN KEY(attempt_id) REFERENCES attempt(attempt_id),
          FOREIGN KEY(quiz_id) REFERENCES quiz(quiz_id)
        );

        CREATE TABLE IF NOT EXISTS feedback (
          feedback_id INTEGER PRIMARY KEY,
          student_id INTEGER NOT NULL,
          rating INTEGER NOT NULL,
          comment TEXT,
          created_at TEXT DEFAULT (datetime('now')),
          FOREIGN KEY(student_id) REFERENCES student(student_id)
        );
        """
    )
    db.commit()


def ensure_columns(db):
    def column_missing(table, column):
        cur = db.execute(f"PRAGMA table_info({table})")
        cols = [row[1] for row in cur.fetchall()]
        return column not in cols

    if column_missing("quiz", "two_category"):
        db.execute("ALTER TABLE quiz ADD COLUMN two_category TEXT")
    if column_missing("attempt", "source"):
        db.execute("ALTER TABLE attempt ADD COLUMN source TEXT DEFAULT 'live'")
    if column_missing("response", "response_time_s"):
        db.execute("ALTER TABLE response ADD COLUMN response_time_s REAL DEFAULT 0")
    db.commit()


def ensure_question_bank(db):
    for item in QUESTION_BANK:
        options_json = json.dumps(item["options"])
        cur = db.execute(
            "SELECT quiz_id FROM quiz WHERE question = ?",
            (item["question"],),
        )
        row = cur.fetchone()
        if row:
            db.execute(
                """
                UPDATE quiz
                SET options_text = ?, correct_answer = ?, two_category = ?, explanation = ?
                WHERE quiz_id = ?
                """,
                (options_json, item["correct"], item["topic"], item["explanation"], row["quiz_id"]),
            )
        else:
            db.execute(
                """
                INSERT INTO quiz (question, options_text, correct_answer, two_category, explanation)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item["question"], options_json, item["correct"], item["topic"], item["explanation"]),
            )
    db.commit()


NORMALIZATION_KEYWORDS = [
    "normalization",
    "1nf",
    "2nf",
    "3nf",
    "functional dependency",
    "determinant",
    "partial dependency",
    "transitive",
    "anomaly",
    "bcnf",
    "decomposition",
    "lossless",
    "dependency",
]

FUNDAMENTAL_KEYWORDS = [
    "dbms",
    "database",
    "table",
    "row",
    "column",
    "primary key",
    "foreign key",
    "candidate key",
    "entity",
    "relationship",
    "attribute",
    "cardinality",
    "schema",
    "er",
    "er-diagram",
    "sql",
    "ddl",
    "dml",
    "data model",
]


def autotag_two_category(text):
    lowered = text.lower()
    norm_match = any(keyword in lowered for keyword in NORMALIZATION_KEYWORDS)
    fund_match = any(keyword in lowered for keyword in FUNDAMENTAL_KEYWORDS)
    if norm_match:
        return TOPICS[1]
    if fund_match:
        return TOPICS[0]
    return ""


def auto_tag_questions(db):
    cur = db.execute(
        "SELECT quiz_id, question, two_category FROM quiz WHERE two_category IS NULL OR two_category = ''"
    )
    to_update = []
    for row in cur.fetchall():
        suggested = autotag_two_category(row["question"])
        if suggested:
            to_update.append((suggested, row["quiz_id"]))
        else:
            app.logger.warning("Auto-tag skipped for quiz_id=%s", row["quiz_id"])
    for topic, quiz_id in to_update:
        db.execute("UPDATE quiz SET two_category = ? WHERE quiz_id = ?", (topic, quiz_id))
    if to_update:
        db.commit()


def purge_legacy_content(db):
    placeholders = ",".join("?" for _ in TOPICS)
    query = f"SELECT quiz_id FROM quiz WHERE two_category IS NULL OR two_category = '' OR two_category NOT IN ({placeholders})"
    cur = db.execute(query, TOPICS)
    quiz_ids = [row["quiz_id"] for row in cur.fetchall()]
    if quiz_ids:
        id_placeholders = ",".join("?" for _ in quiz_ids)
        db.execute(
            f"DELETE FROM response WHERE quiz_id IN ({id_placeholders})",
            quiz_ids,
        )
        db.execute(
            f"DELETE FROM quiz WHERE quiz_id IN ({id_placeholders})",
            quiz_ids,
        )
        db.commit()
        app.logger.info("Purged %d legacy quiz items", len(quiz_ids))
    cur = db.execute("SELECT COUNT(*) AS cnt FROM quiz")
    count = cur.fetchone()["cnt"]
    if count != 30:
        app.logger.warning("Question bank must be exactly 30 (current=%s)", count)


def seed_lecturer(db):
    cur = db.execute("SELECT lecturer_id FROM lecturer WHERE email = ?", ("admin@lct.edu",))
    if not cur.fetchone():
        password_hash = generate_password_hash("Admin123!")
        db.execute(
            "INSERT INTO lecturer (name, email, password_hash) VALUES (?, ?, ?)",
            ("Admin Lecturer", "admin@lct.edu", password_hash),
        )
        db.commit()
        app.logger.info("Seeded default lecturer account")


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def get_time_now():
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
        except Exception:
            return datetime.now()
    return datetime.now()


def format_dt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "role" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def lecturer_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "lecturer":
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def student_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "student":
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():
    if session.get("role") == "student":
        student_id = session.get("student_id")
        db = get_db()
        cur = db.execute(
            "SELECT attempt_id FROM attempt WHERE student_id = ? AND finished_at IS NOT NULL ORDER BY datetime(finished_at) DESC LIMIT 1",
            (student_id,),
        )
        row = cur.fetchone()
        if row:
            return redirect(url_for("review", attempt_id=row["attempt_id"]))
        return redirect(url_for("quiz"))
    if session.get("role") == "lecturer":
        return redirect(url_for("admin_home"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or not password:
            flash("All fields are required.")
            return render_template("register.html", title="Register")
        db = get_db()
        cur = db.execute("SELECT student_id FROM student WHERE email = ?", (email,))
        if cur.fetchone():
            flash("Email already registered.")
            return render_template("register.html", title="Register")
        password_hash = generate_password_hash(password)
        db.execute(
            "INSERT INTO student (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        db.commit()
        cur = db.execute("SELECT student_id FROM student WHERE email = ?", (email,))
        student = cur.fetchone()
        session["role"] = "student"
        session["student_id"] = student["student_id"]
        session["student_name"] = name
        return redirect(url_for("quiz"))
    return render_template("register.html", title="Register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        cur = db.execute("SELECT * FROM student WHERE email = ?", (email,))
        student = cur.fetchone()
        if student and student["password_hash"] and check_password_hash(student["password_hash"], password):
            session.clear()
            session.update(
                {
                    "role": "student",
                    "student_id": student["student_id"],
                    "student_name": student["name"],
                }
            )
            cur = db.execute(
                "SELECT attempt_id FROM attempt WHERE student_id = ? AND finished_at IS NOT NULL ORDER BY datetime(finished_at) DESC LIMIT 1",
                (student["student_id"],),
            )
            last_attempt = cur.fetchone()
            if last_attempt:
                return redirect(url_for("review", attempt_id=last_attempt["attempt_id"]))
            return redirect(url_for("quiz"))
        cur = db.execute("SELECT * FROM lecturer WHERE email = ?", (email,))
        lecturer = cur.fetchone()
        if lecturer and check_password_hash(lecturer["password_hash"], password):
            session.clear()
            session.update(
                {
                    "role": "lecturer",
                    "lecturer_id": lecturer["lecturer_id"],
                    "lecturer_name": lecturer["name"],
                }
            )
            return redirect(url_for("admin_home"))
        flash("Invalid credentials. Please try again.")
    return render_template("login.html", title="Login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/quiz")
@student_required
def quiz():
    db = get_db()
    now = format_dt(get_time_now())
    cur = db.execute(
        "INSERT INTO attempt (student_id, nf_scope, started_at, source) VALUES (?, ?, ?, ?)",
        (session["student_id"], "full-quiz", now, "live"),
    )
    attempt_id = cur.lastrowid
    db.commit()
    session["last_attempt_id"] = attempt_id
    return render_template(
        "quiz.html",
        title="Quiz",
        attempt_id=attempt_id,
        student_id=session["student_id"],
    )


@app.route("/api/quiz_progressive")
@student_required
def api_quiz_progressive():
    db = get_db()
    cur = db.execute(
        "SELECT quiz_id, question, options_text, correct_answer, two_category FROM quiz ORDER BY quiz_id"
    )
    questions = cur.fetchall()
    items = []
    for row in questions:
        options = json.loads(row["options_text"]) if row["options_text"] else []
        labeled = list(zip(["A", "B", "C", "D"], options))
        random.shuffle(labeled)
        randomized = []
        for idx, (original_label, text) in enumerate(labeled):
            randomized.append(
                {
                    "label": chr(ord("A") + idx),
                    "text": text,
                    "value": original_label,
                }
            )
        items.append(
            {
                "quiz_id": row["quiz_id"],
                "question": row["question"],
                "options": randomized,
                "two_category": row["two_category"],
            }
        )
    random.shuffle(items)
    return jsonify(items)


@app.route("/submit", methods=["POST"])
@student_required
def submit_quiz():
    payload = request.get_json(force=True)
    student_id = session.get("student_id")
    attempt_id_raw = payload.get("attempt_id")
    answers = payload.get("answers", [])
    if attempt_id_raw is None or not answers:
        abort(400)
    try:
        attempt_id = int(attempt_id_raw)
    except (TypeError, ValueError):
        abort(400)
    db = get_db()
    cur = db.execute(
        "SELECT attempt_id FROM attempt WHERE attempt_id = ? AND student_id = ?",
        (attempt_id, student_id),
    )
    if not cur.fetchone():
        abort(403)
    db.execute("DELETE FROM response WHERE attempt_id = ?", (attempt_id,))
    total_correct = 0
    for ans in answers:
        quiz_id = ans.get("quiz_id")
        answer = ans.get("answer")
        time_sec = ans.get("time_sec") or 0
        if not quiz_id:
            continue
        cur = db.execute(
            "SELECT correct_answer FROM quiz WHERE quiz_id = ?",
            (quiz_id,),
        )
        quiz_row = cur.fetchone()
        if not quiz_row:
            continue
        correct_answer = quiz_row["correct_answer"]
        score = 1 if answer == correct_answer else 0
        total_correct += score
        db.execute(
            """
            INSERT INTO response (student_id, attempt_id, quiz_id, answer, score, response_time_s)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
        (student_id, attempt_id, quiz_id, answer, score, float(time_sec)),
        )
    db.execute(
        """
        UPDATE attempt
        SET items_total = ?, items_correct = ?, score_pct = ?, finished_at = ?, source = 'live'
        WHERE attempt_id = ?
        """,
        (
            30,
            total_correct,
            round((total_correct / 30) * 100, 2),
            format_dt(get_time_now()),
            attempt_id,
        ),
    )
    db.commit()
    session["last_attempt_id"] = attempt_id
    app.logger.info(
        "[SUBMIT] sid=%s attempt=%s total=30 correct=%s pct=%.2f",
        student_id,
        attempt_id,
        total_correct,
        round((total_correct / 30) * 100, 2),
    )
    score_pct = round((total_correct / 30) * 100, 2)
    redirect_url = url_for("review", attempt_id=int(attempt_id))
    return jsonify(
        {
            "ok": True,
            "attempt_id": int(attempt_id),
            "total": int(30),
            "correct": int(total_correct),
            "score_pct": float(score_pct),
            "redirect_url": redirect_url,
        }
    )


def fetch_attempt_with_responses(attempt_id, student_id=None):
    db = get_db()
    params = [attempt_id]
    query = """
        SELECT a.*, s.name AS student_name
        FROM attempt a
        JOIN student s ON s.student_id = a.student_id
        WHERE a.attempt_id = ?
    """
    if student_id is not None:
        query += " AND a.student_id = ?"
        params.append(student_id)
    cur = db.execute(query, params)
    attempt = cur.fetchone()
    if not attempt:
        return None, []
    cur = db.execute(
        """
        SELECT r.*, q.question, q.options_text, q.correct_answer, q.two_category, q.explanation
        FROM response r
        JOIN quiz q ON q.quiz_id = r.quiz_id
        WHERE r.attempt_id = ?
        ORDER BY r.response_id
        """,
        (attempt_id,),
    )
    responses = cur.fetchall()
    return attempt, responses


@app.route("/review/<int:attempt_id>")
@login_required
def review(attempt_id):
    student_id = session.get("student_id") if session.get("role") == "student" else None
    attempt, responses = fetch_attempt_with_responses(attempt_id, student_id)
    if not attempt:
        abort(404)
    per_topic = {topic: {"correct": 0, "total": 0} for topic in TOPICS}
    review_items = []
    for resp in responses:
        options = json.loads(resp["options_text"]) if resp["options_text"] else []
        options_with_labels = list(zip(["A", "B", "C", "D"], options))
        correct_text = next((text for label, text in options_with_labels if label == resp["correct_answer"]), "")
        selected_text = next((text for label, text in options_with_labels if label == resp["answer"]), "")
        topic = resp["two_category"] or "Unknown"
        if topic in per_topic:
            per_topic[topic]["total"] += 1
            per_topic[topic]["correct"] += resp["score"]
        review_items.append(
            {
                "question": resp["question"],
                "your_answer_label": resp["answer"],
                "your_answer_text": selected_text,
                "correct_label": resp["correct_answer"],
                "correct_text": correct_text,
                "is_correct": bool(resp["score"]),
                "explanation": resp["explanation"],
                "topic": topic,
            }
        )
    attempt_topic_pct = []
    for topic, stats in per_topic.items():
        pct = 0
        if stats["total"]:
            pct = round((stats["correct"] / stats["total"]) * 100, 2)
        attempt_topic_pct.append({"topic": topic, "percent": pct})

    db = get_db()
    cur = db.execute(
        """
        SELECT a.attempt_id, q.two_category, SUM(r.score) AS correct, COUNT(r.response_id) AS total
        FROM attempt a
        JOIN response r ON r.attempt_id = a.attempt_id
        JOIN quiz q ON q.quiz_id = r.quiz_id
        WHERE a.student_id = ?
        GROUP BY a.attempt_id, q.two_category
        """,
        (attempt["student_id"],),
    )
    best_by_topic = {topic: 0 for topic in TOPICS}
    for row in cur.fetchall():
        topic = row["two_category"]
        if topic not in best_by_topic or row["total"] == 0:
            continue
        pct = round((row["correct"] / row["total"]) * 100, 2)
        if pct > best_by_topic[topic]:
            best_by_topic[topic] = pct
    unlocked = all(best_by_topic.get(topic, 0) == 100 for topic in TOPICS)

    feedback_submitted = request.args.get("feedback") == "1"

    return render_template(
        "review.html",
        title="Review",
        attempt=attempt,
        review_items=review_items,
        attempt_topic_pct=attempt_topic_pct,
        best_by_topic=best_by_topic,
        unlocked=unlocked,
        feedback_submitted=feedback_submitted,
    )


@app.route("/thanks")
@student_required
def thanks():
    attempt_id = request.args.get("attempt_id") or session.get("last_attempt_id")
    return render_template("thanks.html", title="Feedback", attempt_id=attempt_id)


@app.route("/api/feedback", methods=["POST"])
@student_required
def api_feedback():
    if request.is_json:
        data = request.get_json()
        rating = data.get("rating")
        comment = data.get("comment", "")
        attempt_id = data.get("attempt_id")
    else:
        rating = request.form.get("rating")
        comment = request.form.get("comment", "")
        attempt_id = request.form.get("attempt_id")
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        flash("Invalid rating submitted.")
        return redirect(url_for("thanks"))
    if rating < 1 or rating > 5:
        flash("Rating must be between 1 and 5.")
        return redirect(url_for("thanks"))
    db = get_db()
    db.execute(
        "INSERT INTO feedback (student_id, rating, comment, created_at) VALUES (?, ?, ?, ?)",
        (
            session["student_id"],
            rating,
            comment.strip(),
            format_dt(get_time_now()),
        ),
    )
    db.commit()
    app.logger.info("[FEEDBACK] sid=%s rating=%s", session["student_id"], rating)
    attempt_id = attempt_id or session.get("last_attempt_id")
    if attempt_id:
        return redirect(url_for("review", attempt_id=attempt_id, feedback=1))
    return redirect(url_for("index"))


@app.route("/student/<int:student_id>")
@login_required
def student_dashboard(student_id):
    role = session.get("role")
    if role == "student" and student_id != session.get("student_id"):
        abort(403)
    db = get_db()
    cur = db.execute(
        "SELECT * FROM student WHERE student_id = ?",
        (student_id,),
    )
    student = cur.fetchone()
    if not student:
        abort(404)
    cur = db.execute(
        """
        SELECT * FROM attempt
        WHERE student_id = ? AND finished_at IS NOT NULL
        ORDER BY datetime(finished_at) DESC
        """,
        (student_id,),
    )
    attempts = cur.fetchall()
    latest_attempt = attempts[0] if attempts else None

    topic_split = [0, 0]
    if latest_attempt:
        cur = db.execute(
            """
            SELECT q.two_category, SUM(r.score) AS correct, COUNT(r.response_id) AS total
            FROM response r
            JOIN quiz q ON q.quiz_id = r.quiz_id
            WHERE r.attempt_id = ?
            GROUP BY q.two_category
            """,
            (latest_attempt["attempt_id"],),
        )
        topic_map = {row["two_category"]: round((row["correct"] / row["total"]) * 100, 2) if row["total"] else 0 for row in cur.fetchall()}
        topic_split = [topic_map.get(topic, 0) for topic in TOPICS]

    cur = db.execute(
        """
        SELECT a.attempt_id, q.two_category, SUM(r.score) AS correct, COUNT(r.response_id) AS total
        FROM attempt a
        JOIN response r ON r.attempt_id = a.attempt_id
        JOIN quiz q ON q.quiz_id = r.quiz_id
        WHERE a.student_id = ?
        GROUP BY a.attempt_id, q.two_category
        """,
        (student_id,),
    )
    best_by_topic = {topic: 0 for topic in TOPICS}
    for row in cur.fetchall():
        topic = row["two_category"]
        if topic not in best_by_topic or row["total"] == 0:
            continue
        pct = round((row["correct"] / row["total"]) * 100, 2)
        if pct > best_by_topic[topic]:
            best_by_topic[topic] = pct
    unlocked = all(best_by_topic.get(topic, 0) == 100 for topic in TOPICS)

    history = []
    for attempt in attempts:
        history.append(
            {
                "attempt_id": attempt["attempt_id"],
                "finished_at": attempt["finished_at"],
                "score_pct": attempt["score_pct"],
            }
        )

    return render_template(
        "student_dashboard.html",
        title="Dashboard",
        student=student,
        latest_attempt=latest_attempt,
        topic_labels=TOPICS,
        topic_split=topic_split,
        history=history,
        unlocked=unlocked,
    )


@app.route("/admin")
@lecturer_required
def admin_home():
    db = get_db()
    totals = {}
    for key, query in {
        "students": "SELECT COUNT(*) AS cnt FROM student",
        "attempts": "SELECT COUNT(*) AS cnt FROM attempt",
        "responses": "SELECT COUNT(*) AS cnt FROM response",
        "attempts_with_responses": "SELECT COUNT(DISTINCT attempt_id) AS cnt FROM response",
    }.items():
        cur = db.execute(query)
        totals[key] = cur.fetchone()["cnt"]

    cur = db.execute(
        """
        SELECT q.two_category, AVG(r.score) * 100 AS accuracy
        FROM response r
        JOIN quiz q ON q.quiz_id = r.quiz_id
        GROUP BY q.two_category
        """,
    )
    accuracies = [
        {
            "topic": row["two_category"],
            "accuracy": round(row["accuracy"], 2) if row["accuracy"] is not None else 0,
        }
        for row in cur.fetchall()
        if row["two_category"] in TOPICS
    ]

    labels = []
    counts_all = []
    counts_resp = []
    now = get_time_now()
    date_labels = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(13, -1, -1)]
    counts_map = {label: 0 for label in date_labels}
    counts_resp_map = {label: 0 for label in date_labels}

    cur = db.execute(
        """
        SELECT DATE(started_at) AS day, COUNT(*) AS cnt
        FROM attempt
        WHERE DATE(started_at) >= DATE('now', '-13 day')
        GROUP BY DATE(started_at)
        """,
    )
    for row in cur.fetchall():
        if row["day"] in counts_map:
            counts_map[row["day"]] = row["cnt"]

    cur = db.execute(
        """
        SELECT DATE(a.started_at) AS day, COUNT(DISTINCT r.attempt_id) AS cnt
        FROM attempt a
        JOIN response r ON r.attempt_id = a.attempt_id
        WHERE DATE(a.started_at) >= DATE('now', '-13 day')
        GROUP BY DATE(a.started_at)
        """,
    )
    for row in cur.fetchall():
        if row["day"] in counts_resp_map:
            counts_resp_map[row["day"]] = row["cnt"]

    for label in date_labels:
        labels.append(label)
        counts_all.append(counts_map[label])
        counts_resp.append(counts_resp_map[label])

    return render_template(
        "admin_home.html",
        title="Lecturer Home",
        totals=totals,
        accuracies=accuracies,
        labels=labels,
        counts_all=counts_all,
        counts_resp=counts_resp,
    )


@app.route("/admin/analytics")
@lecturer_required
def admin_analytics():
    db = get_db()
    cur = db.execute(
        """
        SELECT s.name AS student_name, s.email, q.quiz_id, q.question,
               AVG(r.response_time_s) AS avg_time, COUNT(r.response_id) AS responses
        FROM response r
        JOIN student s ON s.student_id = r.student_id
        JOIN quiz q ON q.quiz_id = r.quiz_id
        GROUP BY r.student_id, r.quiz_id
        ORDER BY avg_time DESC
        """,
    )
    per_student = cur.fetchall()

    cur = db.execute(
        """
        SELECT q.quiz_id, q.question,
               AVG(r.response_time_s) AS avg_time,
               MIN(r.response_time_s) AS min_time,
               MAX(r.response_time_s) AS max_time,
               COUNT(r.response_id) AS responses
        FROM response r
        JOIN quiz q ON q.quiz_id = r.quiz_id
        GROUP BY q.quiz_id
        ORDER BY avg_time DESC
        """,
    )
    per_question = cur.fetchall()

    filtered = [row for row in per_question if row["responses"] >= 5]
    slowest = filtered[:5]
    fastest = list(reversed(filtered[-5:])) if filtered else []

    return render_template(
        "admin_analytics.html",
        title="Analytics",
        per_student=per_student,
        per_question=per_question,
        slowest=slowest,
        fastest=fastest,
    )


@app.route("/admin/rankings")
@lecturer_required
def admin_rankings():
    db = get_db()
    cur = db.execute(
        """
        SELECT s.student_id, s.name, s.email,
               COUNT(a.attempt_id) AS attempts,
               AVG(a.score_pct) AS avg_score,
               MAX(a.score_pct) AS best_score,
               (
                   SELECT score_pct
                   FROM attempt a2
                   WHERE a2.student_id = s.student_id AND a2.finished_at IS NOT NULL
                   ORDER BY datetime(a2.finished_at) DESC
                   LIMIT 1
               ) AS last_score
        FROM student s
        LEFT JOIN attempt a ON a.student_id = s.student_id AND a.finished_at IS NOT NULL
        GROUP BY s.student_id
        ORDER BY avg_score DESC, attempts DESC, s.name ASC
        """,
    )
    rankings = cur.fetchall()
    # SQLite does not support NULLS LAST, so handle in Python
    def sort_key(row):
        avg = row["avg_score"] if row["avg_score"] is not None else -1
        return (-avg, -row["attempts"], row["name"].lower())

    rankings = sorted(rankings, key=sort_key)
    return render_template("admin_rankings.html", title="Rankings", rankings=rankings)


@app.route("/admin/questions")
@lecturer_required
def admin_questions():
    db = get_db()
    placeholders = ",".join("?" for _ in TOPICS)
    cur = db.execute(
        f"""
        SELECT q.quiz_id, q.question, q.two_category,
               COUNT(r.response_id) AS responses,
               AVG(r.score) * 100 AS accuracy
        FROM quiz q
        LEFT JOIN response r ON r.quiz_id = q.quiz_id
        WHERE q.two_category IN ({placeholders})
        GROUP BY q.quiz_id
        ORDER BY q.quiz_id
        """,
        TOPICS,
    )
    questions = [
        {
            "quiz_id": row["quiz_id"],
            "question": row["question"],
            "topic": row["two_category"],
            "responses": row["responses"],
            "accuracy": round(row["accuracy"], 2) if row["accuracy"] is not None else None,
        }
        for row in cur.fetchall()
    ]
    return render_template("admin_questions.html", title="Questions", questions=questions)


@app.context_processor
def inject_globals():
    return {"APP_TITLE": APP_TITLE, "TOPICS": TOPICS}


if __name__ == "__main__":
    app.run(debug=True)
