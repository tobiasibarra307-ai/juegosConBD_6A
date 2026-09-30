# CRUD de usuarios

Aplicación CRUD para la tabla `usuarios`, construida con Python, SQLite y JavaScript sin dependencias externas.

## Ejecutar

```bash
python3 app.py
```

Abre <http://127.0.0.1:8000> en el navegador. La base `usuarios.db` se crea automáticamente al iniciar el servidor.

La tabla `usuarios` usa `usu_id INTEGER PRIMARY KEY AUTOINCREMENT` y los campos `usu_usuario`, `usu_nombre` y `usu_apellido` como `VARCHAR(50)`. Al iniciar, registra a `Tobiasibarra`, `tobias`, `ibarra`.

## API

- `GET /api/usuarios`: lista usuarios.
- `GET /api/usuarios/:id`: consulta un usuario.
- `POST /api/usuarios`: crea un usuario con `usu_usuario`, `usu_nombre` y `usu_apellido`.
- `PUT /api/usuarios/:id`: actualiza esos tres campos.
- `DELETE /api/usuarios/:id`: elimina un usuario.
