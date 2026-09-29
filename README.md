# CRUD de usuarios

Aplicación CRUD para la tabla `usuarios`, construida con Python, SQLite y JavaScript sin dependencias externas.

## Ejecutar

```bash
python3 app.py
```

Abre <http://127.0.0.1:8000> en el navegador. La base `usuarios.db` se crea automáticamente al iniciar el servidor.

## API

- `GET /api/usuarios`: lista usuarios.
- `GET /api/usuarios/:id`: consulta un usuario.
- `POST /api/usuarios`: crea un usuario con `nombre` y `email`.
- `PUT /api/usuarios/:id`: actualiza `nombre` y `email`.
- `DELETE /api/usuarios/:id`: elimina un usuario.
