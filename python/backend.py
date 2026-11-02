"""Backend mínimo para el torneo de fútbol 5."""

import os
import secrets
from contextvars import ContextVar
from functools import wraps

import mysql.connector
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(title="Torneo Fútbol 5")
tokens = {}
current_request = ContextVar("current_request")

DB = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3307")),
    "database": os.getenv("DB_NAME", "torneo_futbol5"),
}
USERS = {
    "administrador": (os.getenv("DB_ADMIN_USER", "admin_torneo"),
                      os.getenv("DB_ADMIN_PASSWORD", "admin1234")),
    "planillero": (os.getenv("DB_PLANILLERO_USER", "planillero_torneo"),
                   os.getenv("DB_PLANILLERO_PASSWORD", "planillero1234")),
}


def db(role="administrador"):
    user, password = USERS[role]
    return mysql.connector.connect(**DB, user=user, password=password)


def query(sql, params=(), role="administrador", many=False):
    connection = db(role)
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.executemany(sql, params) if many else cursor.execute(sql, params)
        result = cursor.fetchall() if cursor.with_rows else []
        connection.commit()
        return result, cursor.lastrowid
    finally:
        cursor.close()
        connection.close()


@app.middleware("http")
async def store_request(request: Request, call_next):
    token = current_request.set(request)
    try:
        return await call_next(request)
    finally:
        current_request.reset(token)


async def payload():
    data = await current_request.get().json()
    if not isinstance(data, dict):
        raise ValueError("El cuerpo debe ser JSON.")
    return data


def required(data, *fields):
    missing = [field for field in fields if data.get(field) in (None, "")]
    if missing:
        raise ValueError("Faltan campos: " + ", ".join(missing))


def session(roles=()):
    token = current_request.get().headers.get("Authorization", "").replace("Bearer ", "")
    user = tokens.get(token)
    if not user:
        raise PermissionError("Autenticación requerida.")
    if roles and user["rol"] not in roles:
        raise PermissionError("Permisos insuficientes.")
    return user


def protected(*roles):
    def decorator(function):
        @wraps(function)
        async def wrapper(*args, **kwargs):
            session(roles)
            return await function(*args, **kwargs)
        return wrapper
    return decorator


@app.exception_handler(ValueError)
async def invalid(_request, error):
    return JSONResponse({"error": str(error)}, status_code=400)


@app.exception_handler(PermissionError)
async def forbidden(_request, error):
    return JSONResponse({"error": str(error)}, status_code=401)


@app.get("/api/health")
async def health():
    try:
        query("SELECT 1")
        return {"status": "ok", "database": "ok"}
    except mysql.connector.Error:
        return JSONResponse(
            {"status": "degraded", "database": "unavailable"}, status_code=503
        )


@app.post("/api/login")
async def login():
    data = await payload()
    required(data, "correo", "contrasena")
    result, _ = query(
        "SELECT correo, rol FROM login WHERE correo=%s AND contrasena=%s",
        (data["correo"], data["contrasena"]),
    )
    if not result:
        return JSONResponse({"error": "Credenciales inválidas"}, status_code=401)
    token = secrets.token_urlsafe(24)
    tokens[token] = result[0]
    return {"token": token, "usuario": result[0]}


@app.get("/api/me")
@protected()
async def me():
    return session()


def resource(table, order=""):
    return query(f"SELECT * FROM {table}{order}", role=session()["rol"])[0]


@app.get("/api/facultades")
@protected()
async def faculties():
    return resource("facultad", " ORDER BY nombre")


@app.get("/api/torneos")
@protected()
async def tournaments():
    return resource("torneo", " ORDER BY anio DESC, semestre DESC")


@app.get("/api/jugadores")
@protected()
async def players():
    return resource("jugador", " ORDER BY apellido, nombre")


@app.post("/api/jugadores")
@protected("administrador")
async def create_player():
    data = await payload()
    required(data, "ci", "nombre", "apellido", "email", "fecha_nacimiento",
             "id_facultad", "tipo")
    query(
        """INSERT INTO jugador
        (ci,nombre,apellido,email,fecha_nacimiento,id_facultad,tipo)
        VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        tuple(data[field] for field in (
            "ci", "nombre", "apellido", "email", "fecha_nacimiento",
            "id_facultad", "tipo",
        )),
    )
    return JSONResponse({"ci": data["ci"]}, status_code=201)


@app.put("/api/jugadores/{ci}")
@protected("administrador")
async def update_player(ci):
    data = await payload()
    fields = ("nombre", "apellido", "email", "fecha_nacimiento", "id_facultad", "tipo")
    values = [(field, data[field]) for field in fields if field in data]
    if not values:
        raise ValueError("No hay campos para modificar.")
    query(
        "UPDATE jugador SET " + ",".join(f"{field}=%s" for field, _ in values)
        + " WHERE ci=%s",
        tuple(value for _, value in values) + (ci,),
    )
    return {"ci": ci}


@app.delete("/api/jugadores/{ci}")
@protected("administrador")
async def delete_player(ci):
    query("DELETE FROM jugador WHERE ci=%s", (ci,))
    return Response(status_code=204)


@app.get("/api/equipos")
@protected()
async def teams():
    return query(
        """SELECT e.*, f.nombre facultad, t.nombre torneo
        FROM equipo e JOIN facultad f ON f.id_facultad=e.id_facultad
        JOIN torneo t ON t.id_torneo=e.id_torneo ORDER BY e.nombre""",
        role=session()["rol"],
    )[0]


@app.get("/api/equipos/{team_id}/plantel")
@protected()
async def roster(team_id):
    return query(
        """SELECT ejt.*, j.nombre, j.apellido, j.tipo
        FROM equipo_jugador_torneo ejt JOIN jugador j ON j.ci=ejt.ci_jugador
        WHERE ejt.id_equipo=%s ORDER BY ejt.numero_camiseta""",
        (team_id,), session()["rol"],
    )[0]


@app.get("/api/complejos")
@protected()
async def complexes():
    return resource("complejo", " ORDER BY nombre")


@app.get("/api/canchas")
@protected()
async def courts():
    return resource("cancha", " ORDER BY id_complejo, nombre_cancha")


@app.get("/api/turnos")
@protected()
async def shifts():
    return resource("turno", " ORDER BY hora_inicio")


@app.get("/api/partidos")
@protected()
async def matches():
    return query(
        """SELECT p.*, l.nombre equipo_local, v.nombre equipo_visitante
        FROM partido p JOIN equipo l ON l.id_equipo=p.id_equipo_local
        JOIN equipo v ON v.id_equipo=p.id_equipo_visitante
        ORDER BY p.dia, p.id_turno""",
        role=session()["rol"],
    )[0]


@app.post("/api/partidos")
@protected("administrador")
async def create_match():
    data = await payload()
    required(data, "id_torneo", "numero_fecha", "id_equipo_local",
             "id_equipo_visitante", "dia", "id_turno", "nombre_cancha",
             "id_complejo")
    if data["id_equipo_local"] == data["id_equipo_visitante"]:
        raise ValueError("Los equipos deben ser distintos.")
    fields = ("id_torneo", "numero_fecha", "id_equipo_local",
              "id_equipo_visitante", "dia", "id_turno", "nombre_cancha",
              "id_complejo")
    _, match_id = query(
        """INSERT INTO partido
        (id_torneo,numero_fecha,id_equipo_local,id_equipo_visitante,dia,
         id_turno,nombre_cancha,id_complejo)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        tuple(data[field] for field in fields),
    )
    return JSONResponse({"id_partido": match_id}, status_code=201)


@app.post("/api/partidos/{match_id}/planilla")
@protected("administrador", "planillero")
async def sheet(match_id):
    data = await payload()
    players = data.get("jugadores", [])
    if not players:
        raise ValueError("Debe indicar los jugadores.")
    query("DELETE FROM planilla_partido WHERE id_partido=%s", (match_id,), session()["rol"])
    query(
        "INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo) VALUES (%s,%s,%s)",
        [(match_id, player["ci_jugador"], player["id_equipo"]) for player in players],
        session()["rol"], many=True,
    )
    query("UPDATE partido SET estado='jugado' WHERE id_partido=%s",
          (match_id,), session()["rol"])
    return Response(status_code=204)


@app.post("/api/partidos/{match_id}/goles")
@protected("administrador", "planillero")
async def goal(match_id):
    data = await payload()
    required(data, "ci_jugador", "minuto")
    _, goal_id = query(
        "INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (%s,%s,%s,%s)",
        (match_id, data["ci_jugador"], data["minuto"], data.get("autogol", False)),
        session()["rol"],
    )
    return JSONResponse({"id_gol": goal_id}, status_code=201)


@app.post("/api/partidos/{match_id}/tarjetas")
@protected("administrador", "planillero")
async def card(match_id):
    data = await payload()
    required(data, "ci_jugador", "minuto", "color")
    if data["color"] not in ("amarilla", "roja"):
        raise ValueError("Color inválido.")
    _, card_id = query(
        "INSERT INTO tarjeta (id_partido,ci_jugador,minuto,color) VALUES (%s,%s,%s,%s)",
        (match_id, data["ci_jugador"], data["minuto"], data["color"]),
        session()["rol"],
    )
    return JSONResponse({"id_tarjeta": card_id}, status_code=201)


@app.get("/api/sanciones")
@protected()
async def sanctions():
    return resource("sancion_jugador", " ORDER BY id_torneo, numero_fecha_inicio")


@app.get("/api/reportes/posiciones/{tournament_id}")
@protected()
async def standings(tournament_id):
    return query(
        """SELECT e.id_equipo, e.nombre, COUNT(DISTINCT p.id_partido) partidos,
        COUNT(g.id_gol) goles
        FROM equipo e LEFT JOIN partido p ON p.id_torneo=e.id_torneo
        AND p.estado='jugado' AND (p.id_equipo_local=e.id_equipo
        OR p.id_equipo_visitante=e.id_equipo)
        LEFT JOIN gol g ON g.id_partido=p.id_partido AND g.autogol=FALSE
        WHERE e.id_torneo=%s GROUP BY e.id_equipo,e.nombre
        ORDER BY goles DESC""",
        (tournament_id,), session()["rol"],
    )[0]


@app.get("/api/reportes/goleadores/{tournament_id}")
@protected()
async def top_scorers(tournament_id):
    return query(
        """SELECT j.ci,j.nombre,j.apellido,COUNT(*) goles
        FROM gol g JOIN jugador j ON j.ci=g.ci_jugador
        JOIN partido p ON p.id_partido=g.id_partido
        WHERE p.id_torneo=%s AND g.autogol=FALSE
        GROUP BY j.ci,j.nombre,j.apellido ORDER BY goles DESC LIMIT 10""",
        (tournament_id,), session()["rol"],
    )[0]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", "5000")),
    )
