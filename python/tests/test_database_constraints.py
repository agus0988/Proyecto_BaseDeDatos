import os
import uuid

import mysql.connector
import pytest


pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DB_HOST"),
    reason="Definí TEST_DB_HOST para ejecutar las pruebas de integración MySQL",
)


@pytest.fixture
def db():
    connection = mysql.connector.connect(
        host=os.environ["TEST_DB_HOST"],
        port=int(os.getenv("TEST_DB_PORT", "3307")),
        database=os.getenv("TEST_DB_NAME", "torneo_futbol5"),
        user=os.getenv("TEST_DB_USER", "admin_torneo"),
        password=os.getenv("TEST_DB_PASSWORD", "admin1234"),
    )
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def crear_contexto(cursor):
    token = uuid.uuid4().hex
    cursor.execute("SELECT id_facultad FROM facultad ORDER BY id_facultad LIMIT 2")
    facultades = [fila[0] for fila in cursor.fetchall()]
    if len(facultades) < 2:
        raise AssertionError("Se necesitan dos facultades para estas pruebas")

    cursor.execute("SELECT anio, semestre FROM torneo")
    existentes = set(cursor.fetchall())
    anio = next(
        (candidato for candidato in range(1900, 32768) if (candidato, 1) not in existentes),
        None,
    )
    if anio is None:
        raise AssertionError("No hay un semestre libre para la prueba")

    cursor.execute(
        "INSERT INTO torneo (nombre, anio, semestre, fecha_inicio, fecha_fin) "
        "VALUES (%s,%s,1,'2026-01-01','2026-12-31')",
        (f"Prueba {token}", anio),
    )
    torneo_id = cursor.lastrowid
    equipos = []
    for indice, facultad_id in enumerate(facultades):
        cursor.execute(
            "INSERT INTO equipo (nombre, id_torneo, id_facultad) VALUES (%s,%s,%s)",
            (f"Equipo {indice} {token}", torneo_id, facultad_id),
        )
        equipos.append(cursor.lastrowid)

    cursor.execute("SELECT nombre_cancha, id_complejo FROM cancha LIMIT 1")
    cancha = cursor.fetchone()
    cursor.execute("SELECT id_turno FROM turno LIMIT 1")
    turno_id = cursor.fetchone()
    if cancha is None or turno_id is None:
        raise AssertionError("Se necesita al menos una cancha y un turno")

    return token, torneo_id, equipos, cancha, turno_id[0]


def crear_jugador(cursor, token, indice, facultad_id):
    ci = str(1_000_000 + (int(token[:7], 16) + indice) % 9_000_000)
    cursor.execute(
        "INSERT INTO jugador "
        "(ci,nombre,apellido,email,fecha_nacimiento,id_facultad,tipo) "
        "VALUES (%s,'Prueba','Integracion',%s,'2000-01-01',%s,'grado')",
        (ci, f"{token}-{indice}@example.test", facultad_id),
    )
    return ci


def insertar_partido(cursor, torneo_id, equipos, cancha, turno_id, fecha, numero_fecha=1):
    cursor.execute(
        "INSERT INTO partido "
        "(id_torneo,numero_fecha,id_equipo_local,id_equipo_visitante,dia,"
        "id_turno,nombre_cancha,id_complejo) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            torneo_id,
            numero_fecha,
            equipos[0],
            equipos[1],
            fecha,
            turno_id,
            cancha[0],
            cancha[1],
        ),
    )


def test_mysql_rechaza_dorsal_duplicado_en_un_equipo(db):
    cursor = db.cursor()
    try:
        token, torneo_id, equipos, _, _ = crear_contexto(cursor)
        cursor.execute("SELECT id_facultad FROM equipo WHERE id_equipo=%s", (equipos[0],))
        facultad_id = cursor.fetchone()[0]
        jugadores = [
            crear_jugador(cursor, token, indice, facultad_id)
            for indice in (1, 2)
        ]
        cursor.execute(
            "INSERT INTO equipo_jugador_torneo "
            "(id_equipo,ci_jugador,id_torneo,numero_camiseta) VALUES (%s,%s,%s,7)",
            (equipos[0], jugadores[0], torneo_id),
        )

        with pytest.raises(mysql.connector.Error):
            cursor.execute(
                "INSERT INTO equipo_jugador_torneo "
                "(id_equipo,ci_jugador,id_torneo,numero_camiseta) VALUES (%s,%s,%s,7)",
                (equipos[0], jugadores[1], torneo_id),
            )
    finally:
        cursor.close()


def test_mysql_rechaza_dos_partidos_en_la_misma_cancha_y_turno(db):
    cursor = db.cursor()
    try:
        _, torneo_id, equipos, cancha, turno_id = crear_contexto(cursor)
        insertar_partido(
            cursor, torneo_id, equipos, cancha, turno_id, "2026-12-01"
        )

        with pytest.raises(mysql.connector.Error):
            insertar_partido(
                cursor, torneo_id, equipos, cancha, turno_id, "2026-12-01",
                numero_fecha=2,
            )
    finally:
        cursor.close()


def test_mysql_rechaza_numero_de_fecha_no_positivo(db):
    cursor = db.cursor()
    try:
        _, torneo_id, equipos, cancha, turno_id = crear_contexto(cursor)

        with pytest.raises(mysql.connector.Error):
            insertar_partido(
                cursor, torneo_id, equipos, cancha, turno_id, "2026-12-01",
                numero_fecha=0,
            )
    finally:
        cursor.close()
