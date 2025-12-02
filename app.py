from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from models.dono import Dono
from models.pet import Pet

app = Flask(__name__)
DB_PATH = "database/petplus.db"

# ----------------- CONEXÃO COM BANCO -----------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ----------------- HOME -----------------
@app.route('/')
def index():
    return render_template('index.html')


# ----------------- DONOS -----------------
@app.route('/donos')
def listar_donos():
    conn = get_db_connection()
    donos = conn.execute("SELECT * FROM donos").fetchall()
    conn.close()
    return render_template('donos.html', donos=donos)


@app.route('/cadastro_dono', methods=['GET', 'POST'])
def cadastro_dono():
    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form['telefone']

        conn = get_db_connection()
        conn.execute("INSERT INTO donos (nome, telefone) VALUES (?, ?)", (nome, telefone))
        conn.commit()
        conn.close()
        return redirect(url_for('listar_donos'))

    return render_template('cadastro_dono.html')


# ---- CRUD DONO ----
@app.route('/dono/<int:id>')
def crud_dono(id):
    conn = get_db_connection()
    dono = conn.execute("SELECT * FROM donos WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template('crud_dono.html', dono=dono)


@app.route('/editar_dono/<int:id>', methods=['GET', 'POST'])
def editar_dono(id):
    conn = get_db_connection()

    if request.method == 'POST':
        nome = request.form['nome']
        telefone = request.form['telefone']

        conn.execute("""
            UPDATE donos SET nome = ?, telefone = ?
            WHERE id = ?
        """, (nome, telefone, id))

        conn.commit()
        conn.close()
        return redirect(url_for('listar_donos'))

    dono = conn.execute("SELECT * FROM donos WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template('editar_dono.html', dono=dono)


@app.route('/excluir_dono/<int:id>', methods=['POST'])
def excluir_dono(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM donos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('listar_donos'))


# ----------------- PETS -----------------
@app.route('/pets')
def listar_pets():
    conn = get_db_connection()
    pets = conn.execute("""
        SELECT pets.*, donos.nome AS dono_nome
        FROM pets LEFT JOIN donos ON pets.dono_id = donos.id
    """).fetchall()
    conn.close()
    return render_template('pets.html', pets=pets)


@app.route('/cadastro_pet', methods=['GET', 'POST'])
def cadastro_pet():
    conn = get_db_connection()
    donos = conn.execute("SELECT * FROM donos").fetchall()

    if request.method == 'POST':
        nome = request.form['nome']
        especie = request.form['especie']
        idade = request.form['idade']
        dono_id = request.form['dono_id']

        conn.execute("""
            INSERT INTO pets (nome, especie, idade, dono_id)
            VALUES (?, ?, ?, ?)
        """, (nome, especie, idade, dono_id))

        conn.commit()
        conn.close()
        return redirect(url_for('listar_pets'))

    conn.close()
    return render_template('cadastro_pet.html', donos=donos)


# ---- CRUD PET ----
@app.route('/pet/<int:id>')
def crud_pet(id):
    conn = get_db_connection()
    pet = conn.execute("""
        SELECT pets.*, donos.nome AS dono_nome
        FROM pets LEFT JOIN donos ON pets.dono_id = donos.id
        WHERE pets.id = ?
    """, (id,)).fetchone()
    conn.close()
    return render_template('crud_pet.html', pet=pet)


@app.route('/editar_pet/<int:id>', methods=['GET', 'POST'])
def editar_pet(id):
    conn = get_db_connection()

    if request.method == 'POST':
        nome = request.form['nome']
        especie = request.form['especie']
        idade = request.form['idade']
        dono_id = request.form['dono_id']

        conn.execute("""
            UPDATE pets
            SET nome = ?, especie = ?, idade = ?, dono_id = ?
            WHERE id = ?
        """, (nome, especie, idade, dono_id, id))

        conn.commit()
        conn.close()
        return redirect(url_for('listar_pets'))

    pet = conn.execute("SELECT * FROM pets WHERE id = ?", (id,)).fetchone()
    donos = conn.execute("SELECT * FROM donos").fetchall()
    conn.close()

    return render_template('editar_pet.html', pet=pet, donos=donos)


@app.route('/excluir_pet/<int:id>', methods=['POST'])
def excluir_pet(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM pets WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('listar_pets'))


# ----------------- RUN -----------------
if __name__ == '__main__':
    app.run(debug=True)
