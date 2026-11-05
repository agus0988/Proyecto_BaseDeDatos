# Torneo Interfacultades 2026

Base de datos y API para administrar un torneo de fútbol 5: equipos, planteles,
partidos, planillas, goles, tarjetas, sanciones y reportes.

## Requisitos

- Docker Desktop con Docker Compose.
- Python 3.12 para ejecutar el menú de terminal (`python/menu.py`).

## Iniciar la aplicación

Desde la raíz del proyecto:

```bash
docker compose up --build
```

La API queda disponible en `http://localhost:8000`. Se usa desde el menú de
terminal descrito más abajo; no hace falta abrir una página web.

MySQL escucha en el puerto `3306` dentro de Docker y Compose lo publica como
`3307` en la computadora (`3307:3306`), accesible desde el equipo en
`localhost:3307`; la API se conecta al servicio `db:3306` dentro de Docker.

Para detener los servicios sin borrar los datos, ejecutá `docker compose down`.
Para recrear la base desde cero y volver a cargar los scripts SQL, ejecutá
`docker compose down -v` y luego `docker compose up --build`.

**Atención:** `down -v` elimina los datos persistidos de la base.

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

2. Abrir otra terminal en la raíz del proyecto y ejecutar el menú:

   ```powershell
   python .\python\menu.py
   ```

   Si ya estás en la carpeta `python`, ejecutá solo `python menu.py`; no
   vuelvas a hacer `cd python`.

3. Dejar la URL predeterminada (`http://localhost:8000`) y escribir el correo y
   la contraseña de prueba cuando los solicite:

   - Administrador: `admin@ucu.edu.uy` / `admin123`
   - Planillero: `planillero@ucu.edu.uy` / `planillero123`

   El menú permite consultar partidos, equipos y planteles. El planillero puede
   cargar jugadores a una planilla, goles y tarjetas. El administrador también
   puede dar de alta, modificar, listar y eliminar jugadores, equipos,
   complejos, canchas, partidos y sanciones; gestionar planteles y torneos; y
   consultar resultados y los 12 reportes. El menú valida formatos básicos y
   la API y MySQL vuelven a validar las reglas de negocio. Los listados se
   muestran en tablas; antes de cada dato, el menú indica el formato admitido,
   como `AAAA-MM-DD` para las fechas, o el rango y las opciones disponibles.

   La contraseña no se muestra mientras se escribe. Para salir, seleccionar
   `0`. El menú consulta el rol asociado a las credenciales para mostrar las
   opciones correctas.

## Estructura

- `db/`: esquema, datos iniciales y vistas/permisos.
- `consultas/consultas.sql`: las 12 consultas SQL solicitadas.
- `Dockerfile`: imagen de la API con dependencias instaladas al construirla.
- `python/api.py`: endpoints de FastAPI.
- `python/menu.py`: menú de terminal que consume la API.
- `python/backend.py`: conexión y operaciones con MySQL por rol.
- `python/consultas.py`: consultas de reportes utilizadas por la API.
- `documentacion/informe.md`: decisiones, mejoras del modelo, bitácora y fuentes.
