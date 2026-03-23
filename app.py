from functools import wraps
import sqlite3
from datetime import date, datetime

from flask import Flask, flash, render_template, request, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models.dono import Dono
from models.pet import Pet

app = Flask(__name__)
app.secret_key = "petplus-admin-auth"
DB_PATH = "database/petplus.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute("""
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
            FOREIGN KEY (dono_id) REFERENCES donos(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pet_vaccines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            vacina_nome TEXT,
            vacina_data TEXT,
            recorrente_anual INTEGER DEFAULT 0,
            FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE
        )
    """)
    pet_columns = [column["name"] for column in conn.execute("PRAGMA table_info(pets)").fetchall()]
    if "user_id" not in pet_columns:
        conn.execute("ALTER TABLE pets ADD COLUMN user_id INTEGER REFERENCES users(id)")
    if "vacina_data" not in pet_columns:
        conn.execute("ALTER TABLE pets ADD COLUMN vacina_data TEXT")
    if "vacina_observacao" not in pet_columns:
        conn.execute("ALTER TABLE pets ADD COLUMN vacina_observacao TEXT")
    if "vacina_recorrente_anual" not in pet_columns:
        conn.execute("ALTER TABLE pets ADD COLUMN vacina_recorrente_anual INTEGER DEFAULT 0")
    if "idade_meses" not in pet_columns:
        conn.execute("ALTER TABLE pets ADD COLUMN idade_meses INTEGER")
    if "peso" not in pet_columns:
        conn.execute("ALTER TABLE pets ADD COLUMN peso REAL")
    if "porte" not in pet_columns:
        conn.execute("ALTER TABLE pets ADD COLUMN porte TEXT")
    existing_single_vaccines = conn.execute("""
        SELECT id, vacina_data, vacina_observacao, vacina_recorrente_anual
        FROM pets
        WHERE vacina_data IS NOT NULL
          AND TRIM(vacina_data) <> ''
          AND NOT EXISTS (
              SELECT 1
              FROM pet_vaccines
              WHERE pet_vaccines.pet_id = pets.id
          )
    """).fetchall()
    for vaccine in existing_single_vaccines:
        conn.execute("""
            INSERT INTO pet_vaccines (pet_id, vacina_nome, vacina_data, recorrente_anual)
            VALUES (?, ?, ?, ?)
        """, (
            vaccine["id"],
            vaccine["vacina_observacao"],
            vaccine["vacina_data"],
            vaccine["vacina_recorrente_anual"] or 0,
        ))
    conn.commit()
    conn.close()


def parse_iso_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def safe_replace_year(source_date, year):
    try:
        return source_date.replace(year=year)
    except ValueError:
        return source_date.replace(year=year, day=28)


def build_vaccine_events(vaccines):
    today = date.today()
    events = []

    for vaccine in vaccines:
        vacina_date = parse_iso_date(vaccine["vacina_data"])
        if not vacina_date:
            continue

        nome_vacina = (vaccine["vacina_nome"] or "Vacina registrada").strip()
        events.append({
            "pet_name": vaccine["pet_nome"],
            "date": vacina_date.isoformat(),
            "title": "Vacina tomada",
            "note": nome_vacina,
            "status": "taken",
        })

        if vaccine["recorrente_anual"]:
            due_year = max(today.year, vacina_date.year + 1)
            due_date = safe_replace_year(vacina_date, due_year)
            if due_date <= vacina_date:
                due_date = safe_replace_year(vacina_date, vacina_date.year + 1)

            days_until_due = (due_date - today).days
            status = "overdue"
            if days_until_due >= 60:
                status = "upcoming"
            elif days_until_due >= 0:
                status = "due"

            events.append({
                "pet_name": vaccine["pet_nome"],
                "date": due_date.isoformat(),
                "title": "Próxima dose",
                "note": nome_vacina,
                "status": status,
            })

    events.sort(key=lambda item: item["date"])
    return events


def collect_vaccines_from_form(form):
    vaccine_names = form.getlist("vacina_nome[]")
    vaccine_dates = form.getlist("vacina_data[]")
    vaccine_recurring = form.getlist("vacina_recorrente_anual[]")
    vaccines = []

    max_len = max(len(vaccine_names), len(vaccine_dates), len(vaccine_recurring), 0)
    for index in range(max_len):
        vacina_nome = vaccine_names[index].strip() if index < len(vaccine_names) else ""
        vacina_data = vaccine_dates[index].strip() if index < len(vaccine_dates) else ""
        recorrente = vaccine_recurring[index].strip() if index < len(vaccine_recurring) else "0"

        if not vacina_nome and not vacina_data:
            continue

        vaccines.append({
            "vacina_nome": vacina_nome or None,
            "vacina_data": vacina_data or None,
            "recorrente_anual": 1 if recorrente == "1" else 0,
        })

    return vaccines


def save_pet_vaccines(conn, pet_id, vaccines):
    conn.execute("DELETE FROM pet_vaccines WHERE pet_id = ?", (pet_id,))
    for vaccine in vaccines:
        conn.execute("""
            INSERT INTO pet_vaccines (pet_id, vacina_nome, vacina_data, recorrente_anual)
            VALUES (?, ?, ?, ?)
        """, (
            pet_id,
            vaccine["vacina_nome"],
            vaccine["vacina_data"],
            vaccine["recorrente_anual"],
        ))


def build_primary_vaccine_fields(vaccines):
    if not vaccines:
        return None, None, 0
    primary_vaccine = vaccines[0]
    return (
        primary_vaccine["vacina_data"],
        primary_vaccine["vacina_nome"],
        primary_vaccine["recorrente_anual"],
    )


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("username"):
            flash("Faça login para continuar.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("username"):
            flash("Faça login para continuar.")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Somente o administrador pode acessar essa área.")
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped_view


def user_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("username"):
            flash("Faça login para continuar.")
            return redirect(url_for("login"))
        if session.get("role") != "user":
            flash("Essa área é exclusiva para usuários clientes.")
            return redirect(url_for("index"))
        return view(*args, **kwargs)

    return wrapped_view


def password_matches(stored_password, provided_password):
    if stored_password == provided_password:
        return True
    try:
        return check_password_hash(stored_password, provided_password)
    except ValueError:
        return False


@app.context_processor
def inject_auth():
    return {
        "is_admin": session.get("role") == "admin",
        "is_user": session.get("role") == "user",
        "is_logged_in": bool(session.get("username")),
        "current_user_name": session.get("display_name"),
    }


init_db()


@app.route("/")
def index():
    if session.get("role") == "user":
        return redirect(url_for("meus_pets"))

    total_donos = 0
    total_pets = 0
    media_idade = 0
    pets_recentes = []

    if session.get("role") == "admin":
        conn = get_db_connection()
        total_donos = conn.execute("SELECT COUNT(*) FROM donos").fetchone()[0]
        total_pets = conn.execute("SELECT COUNT(*) FROM pets").fetchone()[0]
        media_idade = conn.execute("SELECT ROUND(AVG(idade), 1) FROM pets").fetchone()[0]
        pets_recentes = conn.execute("""
            SELECT pets.nome, pets.especie, donos.nome AS dono_nome
            FROM pets
            LEFT JOIN donos ON pets.dono_id = donos.id
            ORDER BY pets.id DESC
            LIMIT 3
        """).fetchall()
        conn.close()

    return render_template(
        "index.html",
        total_donos=total_donos,
        total_pets=total_pets,
        media_idade=media_idade if media_idade is not None else 0,
        pets_recentes=pets_recentes
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        senha = request.form["senha"]

        if username == "admin" and senha == "123":
            session.clear()
            session["username"] = "admin"
            session["display_name"] = "Administrador"
            session["role"] = "admin"
            flash("Login de administrador realizado com sucesso.")
            return redirect(url_for("index"))

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if user and password_matches(user["senha"], senha):
            session.clear()
            session["username"] = user["username"]
            session["display_name"] = user["nome"]
            session["user_id"] = user["id"]
            session["role"] = "user"
            flash("Login realizado com sucesso.")
            return redirect(url_for("meus_pets"))

        flash("Usuário ou senha inválidos.")

    return render_template("login.html")


@app.route("/cadastro_usuario", methods=["GET", "POST"])
def cadastro_usuario():
    if request.method == "POST":
        nome = request.form["nome"].strip()
        username = request.form["username"].strip()
        senha = request.form["senha"]

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO users (nome, username, senha) VALUES (?, ?, ?)",
                (nome, username, generate_password_hash(senha, method="pbkdf2:sha256"))
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("Esse nome de usuário já está em uso.")
            return render_template("cadastro_usuario.html")

        conn.close()
        flash("Conta criada com sucesso. Faça login para entrar.")
        return redirect(url_for("login"))

    return render_template("cadastro_usuario.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Você saiu da sua conta.")
    return redirect(url_for("index"))


@app.route("/meus_pets")
@user_required
def meus_pets():
    conn = get_db_connection()
    pets = conn.execute("""
        SELECT pets.id, pets.nome, pets.especie, pets.idade, pets.idade_meses, pets.peso, pets.porte,
               donos.nome AS dono_nome, donos.telefone AS dono_telefone
        FROM pets
        LEFT JOIN donos ON pets.dono_id = donos.id
        WHERE pets.user_id = ?
        ORDER BY pets.nome
    """, (session.get("user_id"),)).fetchall()
    vaccines = conn.execute("""
        SELECT pet_vaccines.*, pets.nome AS pet_nome
        FROM pet_vaccines
        INNER JOIN pets ON pets.id = pet_vaccines.pet_id
        WHERE pets.user_id = ?
        ORDER BY pet_vaccines.vacina_data, pet_vaccines.id
    """, (session.get("user_id"),)).fetchall()
    conn.close()
    vaccine_events = build_vaccine_events(vaccines)
    pet_vaccines_map = {}
    for vaccine in vaccines:
        pet_vaccines_map.setdefault(vaccine["pet_id"], []).append(vaccine)
    return render_template(
        "meus_pets.html",
        pets=pets,
        pet_vaccines_map=pet_vaccines_map,
        vaccine_events=vaccine_events,
        today=date.today().isoformat(),
    )


@app.route("/donos")
@admin_required
def listar_donos():
    conn = get_db_connection()
    donos = conn.execute("SELECT * FROM donos").fetchall()
    conn.close()
    return render_template("donos.html", donos=donos)


@app.route("/cadastro_dono", methods=["GET", "POST"])
@admin_required
def cadastro_dono():
    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form["telefone"]

        conn = get_db_connection()
        conn.execute("INSERT INTO donos (nome, telefone) VALUES (?, ?)", (nome, telefone))
        conn.commit()
        conn.close()
        return redirect(url_for("listar_donos"))

    return render_template("cadastro_dono.html")


@app.route("/dono/<int:id>")
@admin_required
def crud_dono(id):
    conn = get_db_connection()
    dono = conn.execute("SELECT * FROM donos WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template("crud_dono.html", dono=dono)


@app.route("/editar_dono/<int:id>", methods=["GET", "POST"])
@admin_required
def editar_dono(id):
    conn = get_db_connection()

    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form["telefone"]

        conn.execute("""
            UPDATE donos SET nome = ?, telefone = ?
            WHERE id = ?
        """, (nome, telefone, id))

        conn.commit()
        conn.close()
        return redirect(url_for("listar_donos"))

    dono = conn.execute("SELECT * FROM donos WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template("editar_dono.html", dono=dono)


@app.route("/excluir_dono/<int:id>", methods=["POST"])
@admin_required
def excluir_dono(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM donos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("listar_donos"))


@app.route("/pets")
@admin_required
def listar_pets():
    conn = get_db_connection()
    pets = conn.execute("""
        SELECT pets.*, donos.nome AS dono_nome, users.username AS cliente_username,
               (
                   SELECT COUNT(*)
                   FROM pet_vaccines
                   WHERE pet_vaccines.pet_id = pets.id
               ) AS total_vacinas
        FROM pets
        LEFT JOIN donos ON pets.dono_id = donos.id
        LEFT JOIN users ON pets.user_id = users.id
    """).fetchall()
    conn.close()
    return render_template("pets.html", pets=pets)


@app.route("/cadastro_pet", methods=["GET", "POST"])
@admin_required
def cadastro_pet():
    conn = get_db_connection()
    donos = conn.execute("SELECT * FROM donos").fetchall()
    users = conn.execute("SELECT id, nome, username FROM users ORDER BY username").fetchall()

    if request.method == "POST":
        nome = request.form["nome"]
        especie = request.form["especie"]
        idade = request.form["idade"]
        idade_meses = request.form.get("idade_meses") or None
        peso = request.form.get("peso") or None
        porte = request.form.get("porte") or None
        dono_id = request.form["dono_id"]
        user_id = request.form["user_id"]
        vaccines = collect_vaccines_from_form(request.form)
        vacina_data, vacina_observacao, vacina_recorrente_anual = build_primary_vaccine_fields(vaccines)

        cursor = conn.execute("""
            INSERT INTO pets (
                nome, especie, idade, idade_meses, peso, porte, dono_id, user_id,
                vacina_data, vacina_observacao, vacina_recorrente_anual
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nome, especie, idade, idade_meses, peso, porte, dono_id, user_id, vacina_data, vacina_observacao, vacina_recorrente_anual))
        save_pet_vaccines(conn, cursor.lastrowid, vaccines)

        conn.commit()
        conn.close()
        return redirect(url_for("listar_pets"))

    conn.close()
    return render_template("cadastro_pet.html", donos=donos, users=users)


@app.route("/pet/<int:id>")
@admin_required
def crud_pet(id):
    conn = get_db_connection()
    pet = conn.execute("""
        SELECT pets.*, donos.nome AS dono_nome, users.username AS cliente_username
        FROM pets
        LEFT JOIN donos ON pets.dono_id = donos.id
        LEFT JOIN users ON pets.user_id = users.id
        WHERE pets.id = ?
    """, (id,)).fetchone()
    vaccines = conn.execute("""
        SELECT *
        FROM pet_vaccines
        WHERE pet_id = ?
        ORDER BY vacina_data, id
    """, (id,)).fetchall()
    conn.close()
    return render_template("crud_pet.html", pet=pet, vaccines=vaccines)


@app.route("/editar_pet/<int:id>", methods=["GET", "POST"])
@admin_required
def editar_pet(id):
    conn = get_db_connection()

    if request.method == "POST":
        nome = request.form["nome"]
        especie = request.form["especie"]
        idade = request.form["idade"]
        idade_meses = request.form.get("idade_meses") or None
        peso = request.form.get("peso") or None
        porte = request.form.get("porte") or None
        dono_id = request.form["dono_id"]
        user_id = request.form["user_id"]
        vaccines = collect_vaccines_from_form(request.form)
        vacina_data, vacina_observacao, vacina_recorrente_anual = build_primary_vaccine_fields(vaccines)

        conn.execute("""
            UPDATE pets
            SET nome = ?, especie = ?, idade = ?, idade_meses = ?, peso = ?, porte = ?,
                dono_id = ?, user_id = ?, vacina_data = ?, vacina_observacao = ?, vacina_recorrente_anual = ?
            WHERE id = ?
        """, (nome, especie, idade, idade_meses, peso, porte, dono_id, user_id, vacina_data, vacina_observacao, vacina_recorrente_anual, id))
        save_pet_vaccines(conn, id, vaccines)

        conn.commit()
        conn.close()
        return redirect(url_for("listar_pets"))

    pet = conn.execute("SELECT * FROM pets WHERE id = ?", (id,)).fetchone()
    vaccines = conn.execute("""
        SELECT *
        FROM pet_vaccines
        WHERE pet_id = ?
        ORDER BY vacina_data, id
    """, (id,)).fetchall()
    donos = conn.execute("SELECT * FROM donos").fetchall()
    users = conn.execute("SELECT id, nome, username FROM users ORDER BY username").fetchall()
    conn.close()

    return render_template("editar_pet.html", pet=pet, vaccines=vaccines, donos=donos, users=users)


@app.route("/excluir_pet/<int:id>", methods=["POST"])
@admin_required
def excluir_pet(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM pets WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("listar_pets"))


if __name__ == "__main__":
    app.run(debug=True)
