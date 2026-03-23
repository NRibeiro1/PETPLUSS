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
    idade_meses INTEGER,
    peso REAL,
    porte TEXT,
    dono_id INTEGER,
    user_id INTEGER,
    vacina_data TEXT,
    vacina_observacao TEXT,
    vacina_recorrente_anual INTEGER DEFAULT 0,
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

cursor.execute('''
CREATE TABLE IF NOT EXISTS pet_vaccines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id INTEGER NOT NULL,
    vacina_nome TEXT,
    vacina_data TEXT,
    recorrente_anual INTEGER DEFAULT 0,
    FOREIGN KEY (pet_id) REFERENCES pets (id) ON DELETE CASCADE
)
''')

conn.commit()
conn.close()
print("🐾 Banco de dados criado com sucesso!")
