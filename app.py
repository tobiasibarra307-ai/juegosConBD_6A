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
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "usuario" in tables and "usuarios" not in tables:
            connection.execute("ALTER TABLE usuario RENAME TO usuarios")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE
            )
            """
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
                    "SELECT id, nombre, email FROM usuarios ORDER BY id DESC"
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
                    "SELECT id, nombre, email FROM usuarios WHERE id = ?", (user_id,)
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
            nombre = str(data.get("nombre", "")).strip()
            email = str(data.get("email", "")).strip()
            if not nombre or not email:
                self.send_error_json(400, "Nombre y email son obligatorios")
                return
            with get_connection() as connection:
                cursor = connection.execute(
                    "INSERT INTO usuarios (nombre, email) VALUES (?, ?)",
                    (nombre, email),
                )
                row = connection.execute(
                    "SELECT id, nombre, email FROM usuarios WHERE id = ?",
                    (cursor.lastrowid,),
                ).fetchone()
            self.send_json(201, user_from_row(row))
        except sqlite3.IntegrityError:
            self.send_error_json(409, "El email ya está registrado")
        except ValueError as error:
            self.send_error_json(400, str(error))

    def do_PUT(self):
        user_id = urlparse(self.path).path.rsplit("/", 1)[-1]
        if not user_id.isdigit() or not self.path.startswith("/api/usuarios/"):
            self.send_error_json(404, "Ruta no encontrada")
            return
        try:
            data = self.read_json()
            nombre = str(data.get("nombre", "")).strip()
            email = str(data.get("email", "")).strip()
            if not nombre or not email:
                self.send_error_json(400, "Nombre y email son obligatorios")
                return
            with get_connection() as connection:
                cursor = connection.execute(
                    "UPDATE usuarios SET nombre = ?, email = ? WHERE id = ?",
                    (nombre, email, user_id),
                )
                if cursor.rowcount == 0:
                    self.send_error_json(404, "Usuario no encontrado")
                    return
                row = connection.execute(
                    "SELECT id, nombre, email FROM usuarios WHERE id = ?", (user_id,)
                ).fetchone()
            self.send_json(200, user_from_row(row))
        except sqlite3.IntegrityError:
            self.send_error_json(409, "El email ya está registrado")
        except ValueError as error:
            self.send_error_json(400, str(error))

    def do_DELETE(self):
        user_id = urlparse(self.path).path.rsplit("/", 1)[-1]
        if not user_id.isdigit() or not self.path.startswith("/api/usuarios/"):
            self.send_error_json(404, "Ruta no encontrada")
            return
        with get_connection() as connection:
            cursor = connection.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
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
