import os
import logging
from functools import wraps
from datetime import timedelta

from flask import (
    Flask, render_template, render_template_string,
    request, redirect, url_for, session, flash
)

# Carga variables de entorno desde .env
# pip install python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Conector MySQL opcional
try:
    import mysql.connector  # type: ignore
except Exception:
    mysql = None

from werkzeug.security import check_password_hash, generate_password_hash

# -----------------------------------------------------------------------------
# Configuración base
# -----------------------------------------------------------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)

# Variables de entorno para BD (opcional)
DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")

# Logger básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("duacyd-analitica")


# -----------------------------------------------------------------------------
# Utilidades de sesión / seguridad
# -----------------------------------------------------------------------------
def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("usuario_id"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


# -----------------------------------------------------------------------------
# Conexión a BD (opcional)
# -----------------------------------------------------------------------------
def get_db_connection():
    """
    Intenta conectar a MySQL si hay variables de entorno configuradas.
    Si no hay configuración o falla, retorna None y el sistema usa el modo DEMO.
    """
    if not (DB_HOST and DB_USER and DB_NAME):
        logger.warning("BD no configurada. Modo DEMO activado.")
        return None

    if mysql is None:
        logger.warning("mysql-connector-python no instalado. Modo DEMO activado.")
        return None

    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
        return conn
    except Exception as e:
        logger.error(f"Error conectando a MySQL: {e}")
        return None


def get_user_by_username(username: str):
    """
    Busca al usuario por username en BD.
    Tabla esperada `usuario`:
      id_usuario INT PK AI
      correo VARCHAR(150) UNIQUE
      password_hash VARCHAR(255)
      nombre y apellidos para nombre completo
      rol asignado (opcional)
    """
    conn = get_db_connection()
    if conn is None:
        # Fallback DEMO
        demo = {
            "id": 1,
            "username": "admin",
            "password_hash": generate_password_hash("admin_duacyd"),
            "nombre": "Administración DUACyD",
            "rol": "admin",
        }
        if username == demo["username"]:
            return demo
        return None

    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT
                u.id_usuario AS id,
                u.correo AS username,
                u.password_hash,
                CONCAT(u.nombre, ' ', u.apellidos) AS nombre,
                COALESCE(r.nombre, 'usuario') AS rol
            FROM usuario u
            LEFT JOIN usuario_rol ur ON ur.id_usuario = u.id_usuario
            LEFT JOIN rol r ON r.id_rol = ur.id_rol
            WHERE u.correo = %s
            """,
            (username,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row
    except Exception as e:
        logger.error(f"Error consultando usuario: {e}")
        return None


# -----------------------------------------------------------------------------
# Rutas: Auth y dashboard
# -----------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def root():
    if session.get("usuario_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return render_template("login.html", error="Completa usuario y contraseña.")

        user = get_user_by_username(username)
        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Usuario o contraseña inválidos.")

        # Inicia sesión
        session.permanent = True
        session["usuario_id"] = user["id"]
        session["usuario_username"] = user["username"]
        session["usuario_nombre"] = user.get("nombre") or user["username"]
        session["usuario_rol"] = user.get("rol", "usuario")

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


# -----------------------------------------------------------------------------
# Módulos principales
# -----------------------------------------------------------------------------
# SUAyED: ahora renderiza un submenú propio con cards por carrera
@app.route("/modulo/suayed")
@login_required
def modulo_suayed():
    # Lee (opcional) el periodo seleccionado por querystring para mantener estado
    periodo = request.args.get("periodo")
    return render_template("suayed_menu.html", periodo=periodo)

# Subrutas SUAyED por carrera
@app.route("/modulo/suayed/<carrera>/indicadores")
@login_required
def suayed_indicadores(carrera):
    periodo = request.args.get("periodo")
    titulo = f"Indicadores — {carrera.replace('-', ' ').title()} (SUAyED)"
    cuerpo = [
        "<p>Vista de indicadores en construcción.</p>",
        f"<p><strong>Periodo:</strong> {periodo}</p>" if periodo else ""
    ]
    return render_template_string(_simple_page(titulo, "".join(cuerpo)))


@app.route("/modulo/suayed/<carrera>/cohortes")
@login_required
def suayed_cohortes(carrera):
    periodo = request.args.get("periodo")
    titulo = f"Cohortes — {carrera.replace('-', ' ').title()} (SUAyED)"
    cuerpo = [
        "<p>Vista de cohortes en construcción.</p>",
        f"<p><strong>Periodo:</strong> {periodo}</p>" if periodo else ""
    ]
    return render_template_string(_simple_page(titulo, "".join(cuerpo)))


@app.route("/modulo/suayed/<carrera>/reportes")
@login_required
def suayed_reportes(carrera):
    periodo = request.args.get("periodo")
    titulo = f"Reportes — {carrera.replace('-', ' ').title()} (SUAyED)"
    cuerpo = [
        "<p>Generación y descarga de reportes en construcción.</p>",
        f"<p><strong>Periodo:</strong> {periodo}</p>" if periodo else ""
    ]
    return render_template_string(_simple_page(titulo, "".join(cuerpo)))


# Otros módulos (placeholders)
@app.route("/modulo/edco")
@login_required
def modulo_edco():
    html = _module_placeholder(
        titulo="Educación Continua (EDCO)",
        subtitulo="Cursos, microcursos y diplomados",
        descripcion=(
            "Visualiza oferta, inscripciones, satisfacción, ingresos "
            "y trazabilidad por periodo."
        ),
        icono="bar-chart-line"
    )
    return render_template_string(html)


@app.route("/modulo/cle")
@login_required
def modulo_cle():
    html = _module_placeholder(
        titulo="Centro de Lenguas (CLE)",
        subtitulo="Idiomas y certificaciones",
        descripcion=(
            "Consulta inscritos por idioma y nivel, aprobaciones, "
            "deserción y resultados de exámenes."
        ),
        icono="translate"
    )
    return render_template_string(html)


# -----------------------------------------------------------------------------
# Auxiliares del menú
# -----------------------------------------------------------------------------
@app.route("/ayuda/<modulo>")
@login_required
def ayuda_modulo(modulo: str):
    modulo = (modulo or "").upper()
    cuerpo = f"""
    <p>Esta sección de ayuda describe el uso del módulo <strong>{modulo}</strong>.</p>
    <ul>
      <li>Navega por periodos y filtros en la parte superior.</li>
      <li>Descarga reportes en CSV/XLSX desde el panel correspondiente.</li>
      <li>La ingesta de datos se realiza desde el menú principal &rarr; Plantillas / Ingesta.</li>
    </ul>
    """
    return render_template_string(_simple_page("Ayuda del módulo", cuerpo))


@app.route("/ingesta-datos")
@login_required
def ingesta_datos():
    cuerpo = """
    <p>Aquí podrás cargar datasets (CSV/XLSX) para alimentar los tableros.</p>
    <p>Próximamente: validaciones, vistas previas y bitácora de cargas.</p>
    """
    return render_template_string(_simple_page("Ingesta de datos", cuerpo))


@app.route("/roles-permisos")
@login_required
def roles_permisos():
    cuerpo = """
    <p>Configura quién puede ver, subir y editar información.</p>
    <p>Próximamente: administración de roles, permisos y auditoría.</p>
    """
    return render_template_string(_simple_page("Roles y permisos", cuerpo))


@app.route("/plantillas-datos")
@login_required
def plantillas_datos():
    cuerpo = """
    <p>Descarga formatos y ejemplos para preparar tus archivos de carga.</p>
    <ul>
      <li>Plantilla SUAyED (CSV/XLSX)</li>
      <li>Plantilla EDCO (CSV/XLSX)</li>
      <li>Plantilla CLE (CSV/XLSX)</li>
    </ul>
    """
    return render_template_string(_simple_page("Plantillas de datos", cuerpo))


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("login"))


# -----------------------------------------------------------------------------
# Helpers de HTML minimal (placeholders) para no requerir más plantillas ahora
# -----------------------------------------------------------------------------
def _module_placeholder(titulo: str, subtitulo: str, descripcion: str, icono: str = "grid"):
    """Devuelve una página mínima para un módulo (EDCO/CLE), con Bootstrap."""
    return f"""
    <!doctype html>
    <html lang="es">
    <head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <title>{titulo} — DUACyD Analítica</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
      <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
      <link rel="stylesheet" href="{url_for('static', filename='css/main.css')}">
    </head>
    <body>
      <nav class="navbar navbar-dark topbar">
        <div class="container">
          <a class="navbar-brand d-flex align-items-center gap-2" href="{url_for('dashboard')}">
            <img src="{url_for('static', filename='img/logo_duacyd.png')}" width="24" height="24">
            <span class="fw-bold">DUACyD Analítica</span>
          </a>
          <div class="d-flex align-items-center gap-2">
            <span class="text-white-50 small me-2">
              <i class="bi bi-person-circle me-1"></i>{session.get('usuario_nombre','Usuario')}
            </span>
            <a href="{url_for('logout')}" class="btn btn-outline-light btn-sm">
              <i class="bi bi-box-arrow-right me-1"></i>Salir
            </a>
          </div>
        </div>
      </nav>

      <section class="hero py-4">
        <div class="container">
          <div class="d-flex align-items-center justify-content-between flex-wrap gap-3">
            <div>
              <h1 class="h3 m-0"><i class="bi bi-{icono} me-2"></i>{titulo}</h1>
              <div class="text-muted">{subtitulo}</div>
            </div>
            <span class="tag">En construcción</span>
          </div>
        </div>
      </section>

      <main class="container py-4">
        <div class="row g-4">
          <div class="col-12 col-lg-8">
            <div class="card">
              <div class="card-body">
                <h5 class="card-title">Descripción</h5>
                <p class="mb-0">{descripcion}</p>
              </div>
            </div>
          </div>
          <div class="col-12 col-lg-4">
            <div class="card">
              <div class="card-body">
                <h6 class="card-title">Acciones rápidas</h6>
                <div class="d-grid gap-2">
                  <a class="btn btn-primary" href="{url_for('plantillas_datos')}">
                    <i class="bi bi-filetype-csv me-1"></i> Plantillas de datos
                  </a>
                  <a class="btn btn-outline-secondary" href="{url_for('ingesta_datos')}">
                    <i class="bi bi-upload me-1"></i> Ingesta de datos
                  </a>
                  <a class="btn btn-outline-secondary" href="{url_for('roles_permisos')}">
                    <i class="bi bi-shield-lock me-1"></i> Roles y permisos
                  </a>
                  <a class="btn btn-outline-secondary" href="{url_for('ayuda_modulo', modulo=titulo.split()[0].lower())}">
                    <i class="bi bi-question-circle me-1"></i> Ayuda
                  </a>
                </div>
              </div>
            </div>
            <div class="small text-muted mt-3">
              <i class="bi bi-info-circle me-1"></i> Esta vista es temporal mientras se integran los tableros.
            </div>
          </div>
        </div>
      </main>

      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """


def _simple_page(titulo: str, cuerpo_html: str) -> str:
    """Página auxiliar mínima con Bootstrap para secciones simples."""
    return f"""
    <!doctype html>
    <html lang="es">
    <head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <title>{titulo} — DUACyD Analítica</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
      <link rel="stylesheet" href="{url_for('static', filename='css/main.css')}">
    </head>
    <body>
      <nav class="navbar navbar-dark topbar">
        <div class="container">
          <a class="navbar-brand d-flex align-items-center gap-2" href="{url_for('dashboard')}">
            <img src="{url_for('static', filename='img/logo_duacyd.png')}" width="24" height="24">
            <span class="fw-bold">DUACyD Analítica</span>
          </a>
          <div class="d-flex align-items-center gap-2">
            <span class="text-white-50 small me-2">
              <i class="bi bi-person-circle me-1"></i>{session.get('usuario_nombre','Usuario')}
            </span>
            <a href="{url_for('logout')}" class="btn btn-outline-light btn-sm">
              Salir
            </a>
          </div>
        </div>
      </nav>

      <main class="container py-4">
        <div class="d-flex align-items-center justify-content-between mb-3">
          <h1 class="h4 m-0">{titulo}</h1>
          <a href="{url_for('dashboard')}" class="btn btn-primary">Volver al menú</a>
        </div>
        <div class="card">
          <div class="card-body">
            {cuerpo_html}
          </div>
        </div>
      </main>

      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """


# -----------------------------------------------------------------------------
# Errores
# -----------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template_string(_simple_page("404 — No encontrado", "<p>La ruta solicitada no existe.</p>")), 404


@app.errorhandler(500)
def internal_error(e):
    logger.exception("Error interno del servidor")
    return render_template_string(_simple_page("500 — Error interno", "<p>Ocurrió un error inesperado.</p>")), 500


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
