import sqlite3

conn = sqlite3.connect("feedback.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usn TEXT UNIQUE,
    password TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS feedback(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT,
    department TEXT,
    faculty TEXT,
    feedback TEXT,
    sentiment TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS admin(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT
)
''')

conn.commit()
conn.close()

print("Database Created")