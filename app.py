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
    """Devuelve una página mínima para un módulo (EDCO/CLE) con encabezado unificado."""
    return f"""
    <!doctype html>
    <html lang=\"es\">
    <head>
      <meta charset=\"utf-8\"/>
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
      <title>{titulo} — DUACyD Analítica</title>
      <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
      <link href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css\" rel=\"stylesheet\">
      <link rel=\"stylesheet\" href=\"{url_for('static', filename='css/main.css')}\">
    </head>
    <body class=\"menu-body\">
      <nav class=\"navbar navbar-dark\">
        <div class=\"container\">
          <a class=\"navbar-brand d-flex align-items-center gap-2\" href=\"{url_for('dashboard')}\">\n            <i class=\"bi bi-grid-1x2\"></i>\n            <span class=\"fw-bold\">DUACyD Analítica</span>\n          </a>
          <div class=\"d-flex align-items-center gap-3\">\n            <span class=\"user-badge\">\n              <i class=\"bi bi-person-circle me-2\"></i>{session.get('usuario_nombre','Usuario')}\n            </span>\n            <a href=\"{url_for('logout')}\" class=\"btn btn-outline-light btn-sm\">\n              <i class=\"bi bi-box-arrow-right me-1\"></i>Salir\n            </a>\n          </div>
        </div>
      </nav>

      <div class=\"app-window\">
        <div class=\"app-titlebar\">
          <div class=\"d-flex align-items-center gap-2\">\n            <span class=\"dot red\"></span>\n            <span class=\"dot yellow\"></span>\n            <span class=\"dot green\"></span>\n          </div>
          <div class=\"titlebar-text\">\n            <i class=\"bi bi-{icono} me-2\"></i>{titulo}\n          </div>
        </div>

        <div class=\"app-header\">\n          <div class=\"d-flex justify-content-between align-items-start flex-wrap gap-3\">\n            <div class=\"brand\">\n              <div>\n                <h1>{titulo}</h1>\n                <small>{subtitulo}</small>\n              </div>\n            </div>\n            <div class=\"text-end\">\n              <div class=\"footer-note footer-note-plain\">\n                <i class=\"fas fa-info-circle me-2\"></i> Visualiza y analiza indicadores institucionales\n              </div>\n            </div>\n          </div>\n          <hr>\n        </div>

        <div class=\"app-body\">\n          <div class=\"container\">\n            <div class=\"row g-4\">\n              <div class=\"col-12 col-lg-8\">\n                <div class=\"card\">\n                  <div class=\"card-body\">\n                    <h5 class=\"card-title\">Descripción</h5>\n                    <p class=\"mb-0\">{descripcion}</p>\n                  </div>\n                </div>\n              </div>\n              <div class=\"col-12 col-lg-4\">\n                <div class=\"card\">\n                  <div class=\"card-body\">\n                    <h6 class=\"card-title\">Acciones rápidas</h6>\n                    <div class=\"d-grid gap-2\">\n                      <a class=\"btn btn-primary\" href=\"{url_for('plantillas_datos')}\">\n                        <i class=\"bi bi-filetype-csv me-1\"></i> Plantillas de datos\n                      </a>\n                      <a class=\"btn btn-outline-secondary\" href=\"{url_for('ingesta_datos')}\">\n                        <i class=\"bi bi-upload me-1\"></i> Ingesta de datos\n                      </a>\n                      <a class=\"btn btn-outline-secondary\" href=\"{url_for('roles_permisos')}\">\n                        <i class=\"bi bi-shield-lock me-1\"></i> Roles y permisos\n                      </a>\n                      <a class=\"btn btn-outline-secondary\" href=\"{url_for('ayuda_modulo', modulo=titulo.split()[0].lower())}\">\n                        <i class=\"bi bi-question-circle me-1\"></i> Ayuda\n                      </a>\n                    </div>\n                  </div>\n                </div>\n                <div class=\"small text-muted mt-3\">\n                  <i class=\"bi bi-info-circle me-1\"></i> Vista temporal mientras se integran los tableros.\n                </div>\n              </div>\n            </div>\n          </div>\n        </div>
      </div>

      <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js\"></script>
    </body>
    </html>
    """


def _simple_page(titulo: str, cuerpo_html: str) -> str:
    """Página auxiliar mínima con encabezado unificado."""
    return f"""
    <!doctype html>
    <html lang=\"es\">
    <head>
      <meta charset=\"utf-8\"/>
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>
      <title>{titulo} — DUACyD Analítica</title>
      <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
      <link rel=\"stylesheet\" href=\"{url_for('static', filename='css/main.css')}\">
    </head>
    <body class=\"menu-body\">
      <nav class=\"navbar navbar-dark\">\n        <div class=\"container\">\n          <a class=\"navbar-brand d-flex align-items-center gap-2\" href=\"{url_for('dashboard')}\">\n            <i class=\"bi bi-grid-1x2\"></i>\n            <span class=\"fw-bold\">DUACyD Analítica</span>\n          </a>\n          <div class=\"d-flex align-items-center gap-3\">\n            <span class=\"user-badge\">\n              <i class=\"bi bi-person-circle me-2\"></i>{session.get('usuario_nombre','Usuario')}\n            </span>\n            <a href=\"{url_for('logout')}\" class=\"btn btn-outline-light btn-sm\">Salir</a>\n          </div>\n        </div>\n      </nav>

      <div class=\"app-window\">\n        <div class=\"app-titlebar\">\n          <div class=\"d-flex align-items-center gap-2\">\n            <span class=\"dot red\"></span>\n            <span class=\"dot yellow\"></span>\n            <span class=\"dot green\"></span>\n          </div>\n          <div class=\"titlebar-text\">\n            <i class=\"bi bi-layout-text-window me-2\"></i>{titulo}\n          </div>\n        </div>

        <div class=\"app-header\">\n          <div class=\"d-flex justify-content-between align-items-start flex-wrap gap-3\">\n            <div class=\"brand\">\n              <div>\n                <h1>{titulo}</h1>\n                <small class=\"text-muted\">Sección</small>\n              </div>\n            </div>\n            <div class=\"text-end\">\n              <a href=\"{url_for('dashboard')}\" class=\"btn btn-primary\">Volver al menú</a>\n            </div>\n          </div>\n          <hr>\n        </div>

        <div class=\"app-body\">\n          <div class=\"container\">\n            <div class=\"card\">\n              <div class=\"card-body\">\n                {cuerpo_html}\n              </div>\n            </div>\n          </div>\n        </div>
      </div>

      <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js\"></script>
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
