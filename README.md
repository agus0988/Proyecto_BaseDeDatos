# Torneo Interfacultades 2026

Base de datos y API para administrar un torneo de fútbol 5: equipos, planteles,
partidos, planillas, goles, tarjetas, sanciones y reportes.

## Requisitos

- Docker Desktop con Docker Compose.
- Python 3.12 para ejecutar los tests localmente.

## Iniciar la aplicación

Desde la raíz del proyecto:

```bash
docker compose up
```

La API queda disponible en <http://localhost:8000> y su documentación interactiva
en <http://localhost:8000/docs>.

Para recrear la base desde cero y volver a cargar los scripts SQL:

```bash
docker compose down -v
docker compose up
```

**Atención:** `down -v` elimina los datos persistidos de la base.

MySQL escucha en el puerto `3306` dentro de Docker y Compose lo publica como
`3307` en la computadora (`3307:3306`). Así se evita competir por el puerto
`3306` si ya hay una instalación local de MySQL. La API se conecta al nombre de
servicio `db` en el puerto interno `3306`; desde herramientas locales se usa
`localhost:3307`.

Los scripts `db/01_base.sql`, `db/02_datos.sql` y `db/03_reglas.sql` se ejecutan
en ese orden al inicializar un volumen nuevo. Si Docker ya estaba iniciado,
Compose conserva los datos y MySQL no vuelve a ejecutar los scripts.

## Usuarios de prueba

- Administrador: `admin@ucu.edu.uy` / `admin123`
- Planillero: `planillero@ucu.edu.uy` / `planillero123`

En `/docs`, usar el botón **Authorize** para autenticarse con HTTP Basic.

## Tests

Instalar las dependencias desde la raíz:

```bash
python -m pip install -r requirements.txt
```

Ejecutar la suite:

```bash
cd python
python -m pytest -q
```

Los tests de API usan una base simulada y no requieren que MySQL o Docker estén
activos.

## Estructura

- `db/`: esquema, datos iniciales y vistas/permisos.
- `consultas/consultas.sql`: las 18 consultas SQL de reportes.
- `python/api.py`: endpoints de FastAPI.
- `python/backend.py`: conexión y operaciones con MySQL por rol.
- `python/consultas.py`: consultas de reportes utilizadas por la API.
- `python/tests/`: tests de backend, consultas y API.
- `documentacion/informe.md`: decisiones, mejoras del modelo, bitácora y fuentes.
