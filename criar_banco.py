import sqlite3
import os


db_path = os.path.join("database", "petplus.db")


os.makedirs("database", exist_ok=True)


conn = sqlite3.connect(db_path)
cursor = conn.cursor()


cursor.execute('''
CREATE TABLE IF NOT EXISTS donos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    telefone TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS pets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    especie TEXT,
    idade INTEGER,
    dono_id INTEGER,
    user_id INTEGER,
    FOREIGN KEY (dono_id) REFERENCES donos (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    senha TEXT NOT NULL
)
''')

conn.commit()
conn.close()
print("🐾 Banco de dados criado com sucesso!")
