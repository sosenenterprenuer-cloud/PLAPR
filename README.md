# Personalized Learning Recommendation AI

This repository contains a lightweight Flask application backed by SQLite for delivering a 30-question mastery quiz across two core database concepts.

## Features

- Student self-registration and authentication
- 30-question multiple-choice quiz per attempt covering:
  - Data Modeling & DBMS Fundamentals
  - Normalization & Dependencies
- Randomized question and answer order for every attempt
- Attempt review with explanations, topic analytics, and lifetime-best recommendation unlock
- Student dashboard with charts and attempt history
- Lecturer dashboard with analytics, rankings, and question performance
- Feedback collection and per-question response time tracking
- Utility scripts for maintenance, backups, and CSV seeding

## Getting started

### Prerequisites

- Python 3.9+
- Virtual environment (recommended)

Install dependencies:

```bash
pip install flask werkzeug
```

### Running the app

```bash
cd app
python app.py
```

The application uses the `PLA_DB` environment variable to locate the SQLite database. If unset, it defaults to `app/pla.db`.

### Optional reset run

```bat
cd app
set PLA_DB=%cd%\pla.db
set PLA_RESET=1
python app.py
```

This regenerates the schema and seeds the default lecturer account on first run.

### Maintenance scripts

```bat
python scripts\cleanup_legacy.py
python scripts\seed_demo.py
python scripts\backup_db.py
```

### Seeding from Microsoft Forms CSV

1. Place the exported file at `app\data\msforms_30q_17students.csv`.
2. Run:

```bat
python scripts\seed_from_msforms_csv.py
```

The script validates all 30 questions before inserting the 17 demo students, creates their attempts, and prints credentials.

## Environment variables

- `PLA_DB`: Path to the SQLite database file.
- `PLA_RESET`: When set to `1`, rebuilds the schema and reseeds baseline data on app startup.
- `PLA_SECRET`: Overrides the Flask session secret key.

## License

MIT
