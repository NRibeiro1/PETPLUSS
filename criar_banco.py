import sqlite3
import os

# Caminho do banco de dados
db_path = os.path.join("database", "petplus.db")

# Garante que a pasta 'database' existe
os.makedirs("database", exist_ok=True)

# Conecta ao banco (cria se não existir)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Criação das tabelas
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
    FOREIGN KEY (dono_id) REFERENCES donos (id)
)
''')

conn.commit()
conn.close()
print("🐾 Banco de dados criado com sucesso!")
