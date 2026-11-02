# Torneo Interfacultades 2026

Base de datos y API para administrar un torneo de fútbol 5: equipos, planteles,
partidos, planillas, goles, tarjetas, sanciones y reportes.

## Requisitos

- Docker Desktop con Docker Compose.
- Python 3.12 para ejecutar los tests localmente.

## Iniciar la aplicación

Desde la raíz del proyecto:

```bash
docker compose up --build
```

La API queda disponible en `http://localhost:8000`. Se usa desde el menú de
terminal descrito más abajo; no hace falta abrir una página web.

Para recrear la base desde cero y volver a cargar los scripts SQL:

```bash
docker compose down -v
docker compose up --build
```

**Atención:** `down -v` elimina los datos persistidos de la base.

MySQL escucha en el puerto `3306` dentro de Docker y Compose lo publica como
`3307` en la computadora (`3307:3306`). Así se evita competir por el puerto
`3306` si ya hay una instalación local de MySQL. La API se conecta al nombre de
servicio `db` en el puerto interno `3306`; desde herramientas locales se usa
`localhost:3307`.

Los scripts `db/01_base.sql`, `db/02_datos.sql` y `db/03_vista_y_login.sql`
se ejecutan en ese orden al inicializar un volumen nuevo. MySQL aplica las
restricciones declarativas del esquema (`CHECK`, claves foráneas y `UNIQUE`).
Las reglas que dependen de varias tablas se validan en la API. El proyecto no
usa triggers ni ORM. Si Docker ya estaba iniciado, Compose conserva los datos
y MySQL no vuelve a ejecutar los scripts.

## Usuarios de prueba

- Administrador: `admin@ucu.edu.uy` / `admin123`
- Planillero: `planillero@ucu.edu.uy` / `planillero123`

## Usar desde el menú de terminal

1. En una terminal, desde la raíz del proyecto, iniciar Docker:

   ```bash
   docker compose up --build -d
   docker compose ps
   ```

   Esperar a que `db` figure como `healthy` y `api` como `Up`.

2. Abrir otra terminal en la carpeta `python` y ejecutar el menú:

   ```bash
   cd python
   python menu.py
   ```

3. Dejar la URL predeterminada (`http://localhost:8000`) y escribir el correo y
   la contraseña de prueba cuando los solicite:

   - Administrador: `admin@ucu.edu.uy` / `admin123`
   - Planillero: `planillero@ucu.edu.uy` / `planillero123`

   El menú permite consultar partidos, equipos y planteles. El planillero puede
   cargar jugadores a una planilla, goles y tarjetas. El administrador también
   puede dar de alta, modificar, listar y eliminar jugadores, equipos,
   complejos, canchas, partidos y sanciones; gestionar planteles y torneos; y
   consultar resultados y los 12 reportes. El menú valida formatos básicos y
   la API y MySQL vuelven a validar las reglas de negocio.

   La contraseña no se muestra mientras se escribe. Para salir, seleccionar
   `0`; para detener Docker, ejecutar `docker compose down` en la primera
   terminal. El menú consulta el rol asociado a las credenciales para mostrar
   las opciones correctas.

Para detener los servicios sin borrar los datos:

```bash
docker compose down
```

Solo si se quiere volver a cargar la base de ejemplo desde cero, usar
`docker compose down -v` como se indica arriba; esto elimina los datos
persistidos.

## Tests

Instalar las dependencias desde la raíz:

```bash
python -m pip install -r requirements-dev.txt
```

Ejecutar la suite:

```bash
cd python
python -m pytest -q
```

Los tests de API usan una base simulada y no requieren que MySQL o Docker estén
activos. Las pruebas específicas de reglas MySQL se omiten en esa ejecución.
Para ejecutarlas contra la base local de Docker, iniciá los servicios y, desde
`python`, definí estas variables en PowerShell:

```powershell
$env:TEST_DB_HOST = "127.0.0.1"
$env:TEST_DB_PORT = "3307"
$env:TEST_DB_NAME = "torneo_futbol5"
$env:TEST_DB_USER = "admin_torneo"
$env:TEST_DB_PASSWORD = "admin1234"
python -m pytest -q
```

Esas pruebas usan una transacción y revierten los datos de prueba al terminar.

## Estructura

- `db/`: esquema, datos iniciales y vistas/permisos.
- `consultas/consultas.sql`: las 12 consultas SQL solicitadas.
- `requirements-dev.txt`: dependencias de desarrollo y tests.
- `Dockerfile`: imagen de la API con dependencias instaladas al construirla.
- `python/api.py`: endpoints de FastAPI.
- `python/menu.py`: menú de terminal que consume la API.
- `python/backend.py`: conexión y operaciones con MySQL por rol.
- `python/consultas.py`: consultas de reportes utilizadas por la API.
- `python/tests/`: tests de backend, consultas y API.
- `python/tests/test_database_constraints.py`: pruebas opcionales de restricciones nativas de MySQL.
- `documentacion/informe.md`: decisiones, mejoras del modelo, bitácora y fuentes.
