from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import sqlite3

BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / "usuarios.db"
INDEX_PATH = BASE_DIR / "index.html"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        expected_columns = {
            "usu_id": "INTEGER",
            "usu_usuario": "VARCHAR(50)",
            "usu_nombre": "VARCHAR(50)",
            "usu_apellido": "VARCHAR(50)",
        }
        current_columns = {
            row["name"]: row["type"].upper()
            for row in connection.execute("PRAGMA table_info(usuarios)")
        }

        if current_columns and current_columns != expected_columns:
            old_id = "usu_id" if "usu_id" in current_columns else "id"
            connection.execute("ALTER TABLE usuarios RENAME TO usuarios_anterior")
            connection.execute(
                """
                CREATE TABLE usuarios (
                    usu_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usu_usuario VARCHAR(50),
                    usu_nombre VARCHAR(50),
                    usu_apellido VARCHAR(50)
                )
                """
            )
            connection.execute(
                f"""
                INSERT INTO usuarios
                    (usu_id, usu_usuario, usu_nombre, usu_apellido)
                SELECT {old_id}, usu_usuario, usu_nombre, usu_apellido
                FROM usuarios_anterior
                """
            )
            connection.execute("DROP TABLE usuarios_anterior")
        elif not current_columns:
            connection.execute(
                """
                CREATE TABLE usuarios (
                    usu_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usu_usuario VARCHAR(50),
                    usu_nombre VARCHAR(50),
                    usu_apellido VARCHAR(50)
                )
                """
            )

        updated = connection.execute(
            """
            UPDATE usuarios
            SET usu_usuario = ?, usu_nombre = ?, usu_apellido = ?
            WHERE usu_usuario = ?
            """,
            ("Tobiasibarra", "tobias", "ibarra", "tobias"),
        )
        if updated.rowcount == 0 and connection.execute(
            "SELECT 1 FROM usuarios WHERE usu_usuario = ? LIMIT 1",
            ("Tobiasibarra",),
        ).fetchone() is None:
            connection.execute(
                """
                INSERT INTO usuarios (usu_usuario, usu_nombre, usu_apellido)
                VALUES (?, ?, ?)
                """,
                ("Tobiasibarra", "tobias", "ibarra"),
            )


def user_from_row(row):
    return dict(row)


class RequestHandler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status, message):
        self.send_json(status, {"error": message})

    def read_json(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(content_length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            raise ValueError("El cuerpo debe ser JSON válido")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            body = INDEX_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/usuarios":
            with get_connection() as connection:
                rows = connection.execute(
                    "SELECT usu_id, usu_usuario, usu_nombre, usu_apellido "
                    "FROM usuarios ORDER BY usu_id DESC"
                ).fetchall()
            self.send_json(200, [user_from_row(row) for row in rows])
            return

        if path.startswith("/api/usuarios/"):
            user_id = path.rsplit("/", 1)[-1]
            if not user_id.isdigit():
                self.send_error_json(400, "El id debe ser numérico")
                return
            with get_connection() as connection:
                row = connection.execute(
                    "SELECT usu_id, usu_usuario, usu_nombre, usu_apellido "
                    "FROM usuarios WHERE usu_id = ?",
                    (user_id,),
                ).fetchone()
            if row is None:
                self.send_error_json(404, "Usuario no encontrado")
                return
            self.send_json(200, user_from_row(row))
            return

        self.send_error_json(404, "Ruta no encontrada")

    def do_POST(self):
        if urlparse(self.path).path != "/api/usuarios":
            self.send_error_json(404, "Ruta no encontrada")
            return
        try:
            data = self.read_json()
            usuario = str(data.get("usu_usuario", "")).strip()
            nombre = str(data.get("usu_nombre", "")).strip()
            apellido = str(data.get("usu_apellido", "")).strip()
            if not usuario or not nombre or not apellido:
                self.send_error_json(400, "Usuario, nombre y apellido son obligatorios")
                return
            with get_connection() as connection:
                cursor = connection.execute(
                    "INSERT INTO usuarios (usu_usuario, usu_nombre, usu_apellido) "
                    "VALUES (?, ?, ?)",
                    (usuario, nombre, apellido),
                )
                row = connection.execute(
                    "SELECT usu_id, usu_usuario, usu_nombre, usu_apellido "
                    "FROM usuarios WHERE usu_id = ?",
                    (cursor.lastrowid,),
                ).fetchone()
            self.send_json(201, user_from_row(row))
        except sqlite3.IntegrityError:
            self.send_error_json(409, "El usuario ya está registrado")
        except ValueError as error:
            self.send_error_json(400, str(error))

    def do_PUT(self):
        user_id = urlparse(self.path).path.rsplit("/", 1)[-1]
        if not user_id.isdigit() or not self.path.startswith("/api/usuarios/"):
            self.send_error_json(404, "Ruta no encontrada")
            return
        try:
            data = self.read_json()
            usuario = str(data.get("usu_usuario", "")).strip()
            nombre = str(data.get("usu_nombre", "")).strip()
            apellido = str(data.get("usu_apellido", "")).strip()
            if not usuario or not nombre or not apellido:
                self.send_error_json(400, "Usuario, nombre y apellido son obligatorios")
                return
            with get_connection() as connection:
                cursor = connection.execute(
                    "UPDATE usuarios SET usu_usuario = ?, usu_nombre = ?, "
                    "usu_apellido = ? WHERE usu_id = ?",
                    (usuario, nombre, apellido, user_id),
                )
                if cursor.rowcount == 0:
                    self.send_error_json(404, "Usuario no encontrado")
                    return
                row = connection.execute(
                    "SELECT usu_id, usu_usuario, usu_nombre, usu_apellido "
                    "FROM usuarios WHERE usu_id = ?",
                    (user_id,),
                ).fetchone()
            self.send_json(200, user_from_row(row))
        except sqlite3.IntegrityError:
            self.send_error_json(409, "El usuario ya está registrado")
        except ValueError as error:
            self.send_error_json(400, str(error))

    def do_DELETE(self):
        user_id = urlparse(self.path).path.rsplit("/", 1)[-1]
        if not user_id.isdigit() or not self.path.startswith("/api/usuarios/"):
            self.send_error_json(404, "Ruta no encontrada")
            return
        with get_connection() as connection:
            cursor = connection.execute(
                "DELETE FROM usuarios WHERE usu_id = ?", (user_id,)
            )
        if cursor.rowcount == 0:
            self.send_error_json(404, "Usuario no encontrado")
            return
        self.send_json(200, {"message": "Usuario eliminado"})


if __name__ == "__main__":
    initialize_database()
    server = ThreadingHTTPServer(("127.0.0.1", 8000), RequestHandler)
    print("Servidor disponible en http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
