from pathlib import Path
import sqlite3

root = Path.cwd()
db = root / "data" / "nifty100.db"

print("Project root:", root)
print("Database path:", db)
print("Database exists:", db.is_file())

if db.is_file():
    with sqlite3.connect(str(db)) as con:
        tables = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    print("Tables:", [x[0] for x in tables])
