from __future__ import annotations

from datetime import date
from typing import Literal, Optional

import mysql.connector
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend import execute, fetch_all, fetch_one
import consultas

app = FastAPI(title="Torneo Interfacultades de Futbol 5")
seguridad = HTTPBasic()


@app.exception_handler(mysql.connector.Error)
def error_mysql(_, error: mysql.connector.Error):
    return JSONResponse(status_code=400, content={"error": getattr(error, "msg", str(error))})


def error(mensaje: str):
    raise HTTPException(status_code=400, detail=mensaje)


def usuario_actual(cred: HTTPBasicCredentials = Depends(seguridad)):
    fila = fetch_one(
        "SELECT rol FROM login WHERE correo=%s AND contrasena=SHA2(%s,256)",
        (cred.username, cred.password),
        rol="administrador",
    )
    if not fila:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return fila["rol"]


def solo_admin(rol: str = Depends(usuario_actual)):
    if rol != "administrador":
        raise HTTPException(status_code=403, detail="Forbidden")
    return rol


class EntradaAPI(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class JugadorIn(EntradaAPI):
    ci: str = Field(pattern=r"^\d{6,8}$")
    nombre: str = Field(min_length=1, max_length=50)
    apellido: str = Field(min_length=1, max_length=50)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    fecha_nacimiento: date
    id_facultad: int = Field(gt=0)
    tipo: Literal["grado", "posgrado", "docente", "funcionario"]


class EquipoIn(EntradaAPI):
    nombre: str = Field(min_length=1, max_length=100)
    id_torneo: int = Field(gt=0)
    id_facultad: int = Field(gt=0)
    ci_capitan: Optional[str] = Field(default=None, pattern=r"^\d{6,8}$")


class PlantelIn(EntradaAPI):
    ci_jugador: str = Field(pattern=r"^\d{6,8}$")
    numero_camiseta: int = Field(ge=1, le=99)


class PartidoIn(EntradaAPI):
    id_torneo: int = Field(gt=0)
    numero_fecha: int = Field(gt=0)
    id_equipo_local: int = Field(gt=0)
    id_equipo_visitante: int = Field(gt=0)
    dia: date
    id_turno: int = Field(gt=0)
    nombre_cancha: str = Field(min_length=1, max_length=50)
    id_complejo: int = Field(gt=0)
    estado: Literal["programado", "jugado", "postergado", "cancelado"] = "programado"


class PlanillaIn(EntradaAPI):
    ci_jugador: str = Field(pattern=r"^\d{6,8}$")
    id_equipo: int = Field(gt=0)


class GolIn(EntradaAPI):
    ci_jugador: str = Field(pattern=r"^\d{6,8}$")
    minuto: int = Field(ge=0, le=120)
    autogol: bool = False


class TarjetaIn(EntradaAPI):
    ci_jugador: str = Field(pattern=r"^\d{6,8}$")
    minuto: int = Field(ge=0, le=120)
    color: Literal["amarilla", "roja"]


class SancionIn(EntradaAPI):
    ci_jugador: str = Field(pattern=r"^\d{6,8}$")
    id_torneo: int = Field(gt=0)
    motivo: Literal["roja", "acumulacion de amarillas", "disciplinaria"]
    numero_fecha_inicio: int = Field(gt=0)
    cantidad_fechas: int = Field(ge=1)


class ComplejoIn(EntradaAPI):
    nombre: str = Field(min_length=1, max_length=100)
    direccion: str = Field(min_length=1, max_length=150)
    departamento: str = Field(min_length=1, max_length=50)


class CanchaIn(EntradaAPI):
    nombre_cancha: str = Field(min_length=1, max_length=50)
    superficie: Literal["sintetico", "parquet"]
    techada: bool = False


class CanchaUpdate(EntradaAPI):
    superficie: Literal["sintetico", "parquet"]
    techada: bool = False


class CapitanIn(EntradaAPI):
    ci_jugador: str = Field(pattern=r"^\d{6,8}$")


class EstadoTorneoIn(EntradaAPI):
    estado: Literal["inscripcion", "en curso", "finalizado"]


class TorneoIn(EntradaAPI):
    nombre: str = Field(min_length=1, max_length=100)
    anio: int = Field(ge=2000, le=2100)
    semestre: Literal[1, 2]
    fecha_inicio: date
    fecha_fin: date
    estado: Literal["inscripcion"] = "inscripcion"

    @model_validator(mode="after")
    def validar_fechas(self):
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin debe ser igual o posterior a fecha_inicio")
        return self


# --- Validaciones de negocio ---

def validar_alta_plantel(id_equipo: int, ci: str):
    equipo = fetch_one(
        "SELECT e.id_facultad, t.estado FROM equipo e JOIN torneo t ON t.id_torneo = e.id_torneo WHERE e.id_equipo=%s",
        (id_equipo,),
        rol="administrador",
    )
    jugador = fetch_one("SELECT id_facultad, tipo FROM jugador WHERE ci=%s", (ci,), rol="administrador")
    if not equipo or not jugador:
        error("Equipo o jugador inexistente")
    if equipo["estado"] != "inscripcion":
        error("El plantel solo se modifica en inscripcion")
    if jugador["id_facultad"] != equipo["id_facultad"]:
        error("El jugador es de otra facultad")
    plantel = fetch_one(
        "SELECT COUNT(*) AS total, COALESCE(SUM(CASE WHEN j.tipo IN ('docente','funcionario') THEN 1 ELSE 0 END), 0) AS staff FROM equipo_jugador_torneo e JOIN jugador j ON j.ci = e.ci_jugador WHERE e.id_equipo=%s",
        (id_equipo,),
        rol="administrador",
    )
    if plantel["total"] >= 10:
        error("El plantel ya tiene 10 jugadores")
    if jugador["tipo"] in ("docente", "funcionario") and plantel["staff"] >= 2:
        error("Maximo 2 docentes/funcionarios por plantel")


def validar_baja_plantel(id_equipo: int, ci: str):
    fila = fetch_one(
        "SELECT t.estado, e.ci_capitan FROM equipo e JOIN torneo t ON t.id_torneo = e.id_torneo WHERE e.id_equipo=%s",
        (id_equipo,),
        rol="administrador",
    )
    if not fila:
        error("Equipo inexistente")
    if fila["estado"] != "inscripcion":
        error("El plantel solo se modifica en inscripcion")
    if fila["ci_capitan"] == ci:
        error("No se puede quitar al capitan del plantel")


def validar_capitan(id_equipo: int, ci: str, id_facultad: Optional[int] = None):
    equipo = fetch_one(
        "SELECT e.id_facultad, t.estado FROM equipo e "
        "JOIN torneo t ON t.id_torneo=e.id_torneo WHERE e.id_equipo=%s",
        (id_equipo,),
        rol="administrador",
    )
    if not equipo:
        error("Equipo inexistente")
    if equipo["estado"] != "inscripcion":
        error("El capitan solo se puede asignar o cambiar durante la inscripcion")
    jugador = fetch_one(
        "SELECT id_facultad FROM jugador WHERE ci=%s",
        (ci,),
        rol="administrador",
    )
    if not jugador:
        error("Jugador inexistente")
    facultad_esperada = id_facultad if id_facultad is not None else equipo["id_facultad"]
    if jugador["id_facultad"] != facultad_esperada:
        error("El capitan debe ser de la facultad del equipo")
    if not fetch_one(
        "SELECT 1 AS ok FROM equipo_jugador_torneo WHERE id_equipo=%s AND ci_jugador=%s",
        (id_equipo, ci),
        rol="administrador",
    ):
        error("El capitan debe ser parte del plantel")


def validar_sancion(s: SancionIn):
    torneo = fetch_one(
        "SELECT t.id_torneo, COALESCE(MAX(p.numero_fecha), 0) AS ultima_fecha "
        "FROM torneo t LEFT JOIN partido p ON p.id_torneo=t.id_torneo "
        "WHERE t.id_torneo=%s GROUP BY t.id_torneo",
        (s.id_torneo,),
        rol="administrador",
    )
    if not torneo:
        error("Torneo inexistente")
    if not fetch_one(
        "SELECT 1 AS ok FROM equipo_jugador_torneo "
        "WHERE ci_jugador=%s AND id_torneo=%s",
        (s.ci_jugador, s.id_torneo),
        rol="administrador",
    ):
        error("El jugador no pertenece al torneo")
    if s.numero_fecha_inicio > torneo["ultima_fecha"] + 1:
        error("La fecha de inicio de la sancion no es coherente con el torneo")


def validar_partido(p: PartidoIn, id_partido: int = 0):
    if p.estado != "cancelado":
        if p.id_equipo_local == p.id_equipo_visitante:
            error("Un equipo no puede enfrentarse a si mismo")
        n = fetch_one(
            "SELECT COUNT(*) AS n FROM equipo WHERE id_torneo=%s AND id_equipo IN (%s,%s)",
            (p.id_torneo, p.id_equipo_local, p.id_equipo_visitante),
            rol="administrador",
        )["n"]
        if n != 2:
            error("Ambos equipos deben ser de la misma edicion")
        for eq in (p.id_equipo_local, p.id_equipo_visitante):
            if fetch_one(
                "SELECT COUNT(*) AS n FROM equipo_jugador_torneo WHERE id_equipo=%s",
                (eq,),
                rol="administrador",
            )["n"] < 5:
                error("Cada equipo necesita al menos 5 jugadores")
            capitan = fetch_one(
                "SELECT COUNT(*) AS n FROM equipo e "
                "JOIN jugador j ON j.ci=e.ci_capitan AND j.id_facultad=e.id_facultad "
                "JOIN equipo_jugador_torneo ejt "
                "ON ejt.id_equipo=e.id_equipo AND ejt.ci_jugador=e.ci_capitan "
                "WHERE e.id_equipo=%s AND e.id_torneo=%s",
                (eq, p.id_torneo),
                rol="administrador",
            )
            if capitan["n"] != 1:
                error("Cada equipo debe tener un capitan de su plantel y facultad")
        if fetch_one(
            "SELECT 1 AS ok FROM partido WHERE id_partido<>%s AND id_torneo=%s AND estado<>'cancelado' "
            "AND ((id_equipo_local=%s AND id_equipo_visitante=%s) OR (id_equipo_local=%s AND id_equipo_visitante=%s))",
            (id_partido, p.id_torneo, p.id_equipo_local, p.id_equipo_visitante, p.id_equipo_visitante, p.id_equipo_local),
            rol="administrador",
        ):
            error("Esos equipos ya tienen un partido")
        if fetch_one(
            "SELECT 1 AS ok FROM partido WHERE id_partido<>%s AND id_torneo=%s AND numero_fecha=%s "
            "AND estado<>'cancelado' AND (id_equipo_local IN (%s,%s) OR id_equipo_visitante IN (%s,%s))",
            (id_partido, p.id_torneo, p.numero_fecha, p.id_equipo_local, p.id_equipo_visitante, p.id_equipo_local, p.id_equipo_visitante),
            rol="administrador",
        ):
            error("Un equipo ya juega en esa fecha")
        if fetch_one(
            "SELECT 1 AS ok FROM partido WHERE id_partido<>%s AND estado<>'cancelado' AND dia=%s AND id_turno=%s AND nombre_cancha=%s AND id_complejo=%s",
            (id_partido, p.dia, p.id_turno, p.nombre_cancha, p.id_complejo),
            rol="administrador",
        ):
            error("La cancha ya esta ocupada en ese turno")
    if p.estado == "jugado":
        fila = fetch_one(
            "SELECT CASE WHEN TIMESTAMP(%s, hora_fin) > NOW() THEN 1 ELSE 0 END AS futuro FROM turno WHERE id_turno=%s",
            (p.dia, p.id_turno),
            rol="administrador",
        )
        if not fila or fila["futuro"]:
            error("El partido todavia no se disputo")


def validar_baja_partido(id_partido: int):
    fila = fetch_one("SELECT estado FROM partido WHERE id_partido=%s", (id_partido,), rol="administrador")
    if fila and fila["estado"] == "jugado":
        error("Un partido jugado no se puede eliminar")


def validar_correccion(id_partido: int):
    fila = fetch_one(
        "SELECT p.estado, CASE WHEN TIMESTAMP(p.dia, t.hora_fin) + INTERVAL 48 HOUR < NOW() THEN 1 ELSE 0 END AS vencido "
        "FROM partido p JOIN turno t ON t.id_turno = p.id_turno WHERE p.id_partido=%s",
        (id_partido,),
        rol="administrador",
    )
    if not fila:
        error("Partido inexistente")
    if fila["estado"] == "cancelado":
        error("No se pueden registrar ni corregir eventos de un partido cancelado")
    if fila["estado"] == "jugado" and fila["vencido"]:
        error("Pasaron mas de 48 horas desde el partido")


def validar_planilla(id_partido: int, ci: str, id_equipo: int) -> bool:
    partido = fetch_one(
        "SELECT p.id_torneo, p.numero_fecha, p.estado, p.id_equipo_local, "
        "p.id_equipo_visitante, CASE WHEN TIMESTAMP(p.dia, t.hora_fin) <= NOW() THEN 1 ELSE 0 END AS turno_finalizado "
        "FROM partido p JOIN turno t ON t.id_turno=p.id_turno WHERE p.id_partido=%s",
        (id_partido,),
        rol="administrador",
    )
    if not partido:
        error("Partido inexistente")
    if partido["estado"] == "cancelado":
        error("El partido esta cancelado")
    if partido["estado"] != "jugado" and not partido["turno_finalizado"]:
        error("No se puede cargar la planilla antes de que termine el partido")
    if id_equipo not in (partido["id_equipo_local"], partido["id_equipo_visitante"]):
        error("El equipo no juega ese partido")
    if not fetch_one(
        "SELECT 1 AS ok FROM equipo_jugador_torneo WHERE id_equipo=%s AND ci_jugador=%s",
        (id_equipo, ci),
        rol="administrador",
    ):
        error("El jugador no es del plantel de ese equipo")
    if fetch_one(
        "SELECT 1 AS ok FROM sancion_jugador WHERE ci_jugador=%s AND id_torneo=%s AND %s BETWEEN numero_fecha_inicio AND numero_fecha_inicio + cantidad_fechas - 1",
        (ci, partido["id_torneo"], partido["numero_fecha"]),
        rol="administrador",
    ):
        error("Jugador suspendido")
    validar_correccion(id_partido)
    return bool(partido["turno_finalizado"])


def aplicar_sancion(id_partido: int, ci: str, color: str):
    partido = fetch_one("SELECT id_torneo, numero_fecha FROM partido WHERE id_partido=%s", (id_partido,), rol="administrador")
    if not partido:
        error("Partido inexistente")
    motivo = None
    if color == "roja":
        motivo = "roja"
    else:
        n = fetch_one(
            "SELECT COUNT(*) AS n FROM tarjeta t JOIN partido pa ON pa.id_partido = t.id_partido "
            "WHERE t.ci_jugador=%s AND t.color='amarilla' AND pa.id_torneo=%s",
            (ci, partido["id_torneo"]),
            rol="administrador",
        )["n"]
        if n > 0 and n % 3 == 0:
            motivo = "acumulacion de amarillas"
    if motivo:
        execute(
            "INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas) "
            "VALUES (%s,%s,%s,%s,1)",
            (ci, partido["id_torneo"], motivo, partido["numero_fecha"] + 1),
            rol="administrador",
        )


# --- Endpoints ---

@app.get("/")
def raiz():
    return {"mensaje": "API del torneo activa"}


@app.get("/sesion")
def obtener_sesion(rol: str = Depends(usuario_actual)):
    return {"rol": rol}


@app.get("/jugadores")
def listar_jugadores(_rol: str = Depends(solo_admin)):
    return fetch_all("SELECT * FROM jugador ORDER BY ci")


@app.post("/jugadores", dependencies=[Depends(solo_admin)])
def crear_jugador(j: JugadorIn):
    execute(
        "INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (j.ci, j.nombre, j.apellido, j.email, j.fecha_nacimiento, j.id_facultad, j.tipo),
        rol="administrador",
    )
    return {"mensaje": "Jugador creado"}


@app.put("/jugadores/{ci}", dependencies=[Depends(solo_admin)])
def actualizar_jugador(ci: str, j: JugadorIn):
    jugador_inscripto = fetch_one(
        "SELECT 1 AS ok FROM equipo_jugador_torneo WHERE ci_jugador=%s LIMIT 1",
        (ci,),
        rol="administrador",
    )
    if jugador_inscripto:
        actual = fetch_one(
            "SELECT id_facultad FROM jugador WHERE ci=%s",
            (ci,),
            rol="administrador",
        )
        if actual and j.id_facultad != actual["id_facultad"]:
            error("No se puede cambiar la facultad de un jugador inscripto en un plantel")
    execute(
        "UPDATE jugador SET nombre=%s, apellido=%s, email=%s, fecha_nacimiento=%s, id_facultad=%s, tipo=%s WHERE ci=%s",
        (j.nombre, j.apellido, j.email, j.fecha_nacimiento, j.id_facultad, j.tipo, ci),
        rol="administrador",
    )
    return {"mensaje": "Jugador actualizado"}


@app.delete("/jugadores/{ci}", dependencies=[Depends(solo_admin)])
def eliminar_jugador(ci: str):
    execute("DELETE FROM jugador WHERE ci=%s", (ci,), rol="administrador")
    return {"mensaje": "Jugador eliminado"}


@app.get("/equipos")
def listar_equipos(_rol: str = Depends(usuario_actual)):
    return fetch_all("SELECT * FROM equipo ORDER BY id_equipo")


@app.get("/equipos/{id_equipo}/jugadores")
def listar_jugadores_del_equipo(id_equipo: int, _rol: str = Depends(usuario_actual)):
    return fetch_all(
        "SELECT j.ci, j.nombre, j.apellido, j.tipo, ejt.numero_camiseta "
        "FROM equipo_jugador_torneo ejt JOIN jugador j ON j.ci=ejt.ci_jugador "
        "WHERE ejt.id_equipo=%s ORDER BY ejt.numero_camiseta",
        (id_equipo,),
    )


@app.post("/equipos", dependencies=[Depends(solo_admin)])
def crear_equipo(e: EquipoIn):
    if e.ci_capitan:
        error("Cree el equipo sin capitan; agregue al jugador al plantel y luego asignelo")
    torneo = fetch_one(
        "SELECT estado FROM torneo WHERE id_torneo=%s",
        (e.id_torneo,),
        rol="administrador",
    )
    if not torneo:
        error("Torneo inexistente")
    if torneo["estado"] != "inscripcion":
        error("Solo se pueden agregar equipos durante la inscripcion")
    execute(
        "INSERT INTO equipo (nombre, id_torneo, id_facultad, ci_capitan) VALUES (%s,%s,%s,%s)",
        (e.nombre, e.id_torneo, e.id_facultad, None),
        rol="administrador",
    )
    return {"mensaje": "Equipo creado"}


@app.put("/equipos/{id_equipo}", dependencies=[Depends(solo_admin)])
def actualizar_equipo(id_equipo: int, e: EquipoIn):
    actual = fetch_one(
        "SELECT e.id_facultad, e.ci_capitan, t.estado FROM equipo e "
        "JOIN torneo t ON t.id_torneo=e.id_torneo WHERE e.id_equipo=%s",
        (id_equipo,),
        rol="administrador",
    )
    if not actual:
        error("Equipo inexistente")
    if actual["estado"] == "finalizado":
        error("No se pueden modificar equipos de un torneo finalizado")
    if e.id_facultad != actual["id_facultad"]:
        integrantes = fetch_one(
            "SELECT COUNT(*) AS total FROM equipo_jugador_torneo WHERE id_equipo=%s",
            (id_equipo,),
            rol="administrador",
        )
        if integrantes["total"]:
            error("No se puede cambiar la facultad de un equipo con jugadores en el plantel")
    if e.ci_capitan and e.ci_capitan != actual["ci_capitan"]:
        validar_capitan(id_equipo, e.ci_capitan, e.id_facultad)
    execute(
        "UPDATE equipo SET nombre=%s, id_torneo=%s, id_facultad=%s, ci_capitan=%s WHERE id_equipo=%s",
        (e.nombre, e.id_torneo, e.id_facultad, e.ci_capitan, id_equipo),
        rol="administrador",
    )
    return {"mensaje": "Equipo actualizado"}


@app.delete("/equipos/{id_equipo}", dependencies=[Depends(solo_admin)])
def eliminar_equipo(id_equipo: int):
    execute("DELETE FROM equipo WHERE id_equipo=%s", (id_equipo,), rol="administrador")
    return {"mensaje": "Equipo eliminado"}


@app.post("/equipos/{id_equipo}/jugadores", dependencies=[Depends(solo_admin)])
def agregar_al_plantel(id_equipo: int, j: PlantelIn):
    validar_alta_plantel(id_equipo, j.ci_jugador)
    equipo = fetch_one(
        "SELECT id_torneo FROM equipo WHERE id_equipo=%s",
        (id_equipo,),
        rol="administrador",
    )
    execute(
        "INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) "
        "VALUES (%s,%s,%s,%s)",
        (id_equipo, j.ci_jugador, equipo["id_torneo"], j.numero_camiseta),
        rol="administrador",
    )
    return {"mensaje": "Jugador agregado al plantel"}


@app.delete("/equipos/{id_equipo}/jugadores/{ci}", dependencies=[Depends(solo_admin)])
def quitar_del_plantel(id_equipo: int, ci: str):
    validar_baja_plantel(id_equipo, ci)
    execute("DELETE FROM equipo_jugador_torneo WHERE id_equipo=%s AND ci_jugador=%s", (id_equipo, ci), rol="administrador")
    return {"mensaje": "Jugador quitado del plantel"}


@app.put("/equipos/{id_equipo}/capitan", dependencies=[Depends(solo_admin)])
def cambiar_capitan(id_equipo: int, data: CapitanIn):
    validar_capitan(id_equipo, data.ci_jugador)
    execute("UPDATE equipo SET ci_capitan=%s WHERE id_equipo=%s", (data.ci_jugador, id_equipo), rol="administrador")
    return {"mensaje": "Capitan actualizado"}


@app.get("/complejos")
def listar_complejos(_rol: str = Depends(solo_admin)):
    return fetch_all("SELECT * FROM complejo ORDER BY id_complejo")


@app.post("/complejos", dependencies=[Depends(solo_admin)])
def crear_complejo(payload: ComplejoIn):
    execute(
        "INSERT INTO complejo (nombre, direccion, departamento) VALUES (%s,%s,%s)",
        (payload.nombre, payload.direccion, payload.departamento),
        rol="administrador",
    )
    return {"mensaje": "Complejo creado"}


@app.put("/complejos/{id_complejo}", dependencies=[Depends(solo_admin)])
def actualizar_complejo(id_complejo: int, payload: ComplejoIn):
    execute(
        "UPDATE complejo SET nombre=%s, direccion=%s, departamento=%s WHERE id_complejo=%s",
        (payload.nombre, payload.direccion, payload.departamento, id_complejo),
        rol="administrador",
    )
    return {"mensaje": "Complejo actualizado"}


@app.delete("/complejos/{id_complejo}", dependencies=[Depends(solo_admin)])
def eliminar_complejo(id_complejo: int):
    execute("DELETE FROM complejo WHERE id_complejo=%s", (id_complejo,), rol="administrador")
    return {"mensaje": "Complejo eliminado"}


@app.get("/complejos/{id_complejo}/canchas")
def listar_canchas(id_complejo: int, _rol: str = Depends(solo_admin)):
    return fetch_all("SELECT * FROM cancha WHERE id_complejo=%s ORDER BY nombre_cancha", (id_complejo,))


@app.post("/complejos/{id_complejo}/canchas", dependencies=[Depends(solo_admin)])
def crear_cancha(id_complejo: int, payload: CanchaIn):
    execute(
        "INSERT INTO cancha (nombre_cancha, id_complejo, superficie, techada) VALUES (%s,%s,%s,%s)",
        (payload.nombre_cancha, id_complejo, payload.superficie, payload.techada),
        rol="administrador",
    )
    return {"mensaje": "Cancha creada"}


@app.put("/complejos/{id_complejo}/canchas/{nombre_cancha}", dependencies=[Depends(solo_admin)])
def actualizar_cancha(id_complejo: int, nombre_cancha: str, payload: CanchaUpdate):
    execute(
        "UPDATE cancha SET superficie=%s, techada=%s WHERE nombre_cancha=%s AND id_complejo=%s",
        (payload.superficie, payload.techada, nombre_cancha, id_complejo),
        rol="administrador",
    )
    return {"mensaje": "Cancha actualizada"}


@app.delete("/complejos/{id_complejo}/canchas/{nombre_cancha}", dependencies=[Depends(solo_admin)])
def eliminar_cancha(id_complejo: int, nombre_cancha: str):
    execute("DELETE FROM cancha WHERE nombre_cancha=%s AND id_complejo=%s", (nombre_cancha, id_complejo), rol="administrador")
    return {"mensaje": "Cancha eliminada"}


@app.get("/partidos")
def listar_partidos(_rol: str = Depends(usuario_actual)):
    return fetch_all("SELECT * FROM partido ORDER BY id_torneo, numero_fecha, id_partido")


@app.post("/partidos", dependencies=[Depends(solo_admin)])
def crear_partido(p: PartidoIn):
    validar_partido(p)
    execute(
        "INSERT INTO partido (id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante, dia, id_turno, nombre_cancha, id_complejo, estado) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (p.id_torneo, p.numero_fecha, p.id_equipo_local, p.id_equipo_visitante, p.dia, p.id_turno, p.nombre_cancha, p.id_complejo, p.estado),
        rol="administrador",
    )
    return {"mensaje": "Partido creado"}


@app.put("/partidos/{id_partido}", dependencies=[Depends(solo_admin)])
def actualizar_partido(id_partido: int, p: PartidoIn):
    validar_correccion(id_partido)
    validar_partido(p, id_partido)
    execute(
        "UPDATE partido SET id_torneo=%s, numero_fecha=%s, id_equipo_local=%s, id_equipo_visitante=%s, dia=%s, id_turno=%s, nombre_cancha=%s, id_complejo=%s, estado=%s WHERE id_partido=%s",
        (p.id_torneo, p.numero_fecha, p.id_equipo_local, p.id_equipo_visitante, p.dia, p.id_turno, p.nombre_cancha, p.id_complejo, p.estado, id_partido),
        rol="administrador",
    )
    return {"mensaje": "Partido actualizado"}


@app.delete("/partidos/{id_partido}", dependencies=[Depends(solo_admin)])
def eliminar_partido(id_partido: int):
    validar_baja_partido(id_partido)
    execute("DELETE FROM partido WHERE id_partido=%s", (id_partido,), rol="administrador")
    return {"mensaje": "Partido eliminado"}


@app.post("/partidos/{id_partido}/planilla")
def registrar_planilla(id_partido: int, pl: PlanillaIn, rol: str = Depends(usuario_actual)):
    turno_finalizado = validar_planilla(id_partido, pl.ci_jugador, pl.id_equipo)
    execute(
        "INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES (%s,%s,%s)",
        (id_partido, pl.ci_jugador, pl.id_equipo),
        rol=rol,
    )
    if turno_finalizado:
        execute(
            "UPDATE partido SET estado='jugado' WHERE id_partido=%s AND estado NOT IN ('jugado','cancelado')",
            (id_partido,),
            rol="administrador",
        )
    return {"mensaje": "Jugador agregado a la planilla"}


@app.get("/partidos/{id_partido}/planilla")
def listar_planilla(id_partido: int, _rol: str = Depends(solo_admin)):
    return fetch_all(
        "SELECT pp.id_partido, pp.ci_jugador, pp.id_equipo, j.nombre, j.apellido "
        "FROM planilla_partido pp JOIN jugador j ON j.ci=pp.ci_jugador "
        "WHERE pp.id_partido=%s ORDER BY pp.id_equipo, pp.ci_jugador",
        (id_partido,),
    )


@app.delete("/partidos/{id_partido}/planilla/{ci_jugador}")
def eliminar_planilla(id_partido: int, ci_jugador: str, rol: str = Depends(usuario_actual)):
    validar_correccion(id_partido)
    execute("DELETE FROM planilla_partido WHERE id_partido=%s AND ci_jugador=%s", (id_partido, ci_jugador), rol=rol)
    return {"mensaje": "Jugador quitado de la planilla"}


@app.post("/partidos/{id_partido}/goles")
def registrar_gol(id_partido: int, g: GolIn, rol: str = Depends(usuario_actual)):
    validar_correccion(id_partido)
    execute(
        "INSERT INTO gol (id_partido, ci_jugador, minuto, autogol) VALUES (%s,%s,%s,%s)",
        (id_partido, g.ci_jugador, g.minuto, g.autogol),
        rol=rol,
    )
    return {"mensaje": "Gol registrado"}


@app.get("/partidos/{id_partido}/goles")
def listar_goles(id_partido: int, _rol: str = Depends(solo_admin)):
    return fetch_all(
        "SELECT * FROM gol WHERE id_partido=%s ORDER BY minuto, id_gol",
        (id_partido,),
    )


@app.delete("/partidos/{id_partido}/goles/{id_gol}")
def eliminar_gol(id_partido: int, id_gol: int, rol: str = Depends(usuario_actual)):
    validar_correccion(id_partido)
    execute("DELETE FROM gol WHERE id_gol=%s AND id_partido=%s", (id_gol, id_partido), rol=rol)
    return {"mensaje": "Gol eliminado"}


@app.post("/partidos/{id_partido}/tarjetas")
def registrar_tarjeta(id_partido: int, t: TarjetaIn, rol: str = Depends(usuario_actual)):
    validar_correccion(id_partido)
    execute(
        "INSERT INTO tarjeta (id_partido, ci_jugador, minuto, color) VALUES (%s,%s,%s,%s)",
        (id_partido, t.ci_jugador, t.minuto, t.color),
        rol=rol,
    )
    aplicar_sancion(id_partido, t.ci_jugador, t.color)
    return {"mensaje": "Tarjeta registrada"}


@app.get("/partidos/{id_partido}/tarjetas")
def listar_tarjetas(id_partido: int, _rol: str = Depends(solo_admin)):
    return fetch_all(
        "SELECT * FROM tarjeta WHERE id_partido=%s ORDER BY minuto, id_tarjeta",
        (id_partido,),
    )


@app.delete("/partidos/{id_partido}/tarjetas/{id_tarjeta}")
def eliminar_tarjeta(id_partido: int, id_tarjeta: int, rol: str = Depends(usuario_actual)):
    validar_correccion(id_partido)
    execute("DELETE FROM tarjeta WHERE id_tarjeta=%s AND id_partido=%s", (id_tarjeta, id_partido), rol=rol)
    return {"mensaje": "Tarjeta eliminada"}


@app.get("/sanciones")
def listar_sanciones(_rol: str = Depends(solo_admin)):
    return fetch_all("SELECT * FROM sancion_jugador ORDER BY id_torneo, id_sancion")


@app.post("/sanciones", dependencies=[Depends(solo_admin)])
def crear_sancion(s: SancionIn):
    validar_sancion(s)
    execute(
        "INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas) VALUES (%s,%s,%s,%s,%s)",
        (s.ci_jugador, s.id_torneo, s.motivo, s.numero_fecha_inicio, s.cantidad_fechas),
        rol="administrador",
    )
    return {"mensaje": "Sancion creada"}


@app.put("/sanciones/{id_sancion}", dependencies=[Depends(solo_admin)])
def actualizar_sancion(id_sancion: int, s: SancionIn):
    validar_sancion(s)
    execute(
        "UPDATE sancion_jugador SET ci_jugador=%s, id_torneo=%s, motivo=%s, numero_fecha_inicio=%s, cantidad_fechas=%s WHERE id_sancion=%s",
        (s.ci_jugador, s.id_torneo, s.motivo, s.numero_fecha_inicio, s.cantidad_fechas, id_sancion),
        rol="administrador",
    )
    return {"mensaje": "Sancion actualizada"}


@app.delete("/sanciones/{id_sancion}", dependencies=[Depends(solo_admin)])
def eliminar_sancion(id_sancion: int):
    execute("DELETE FROM sancion_jugador WHERE id_sancion=%s", (id_sancion,), rol="administrador")
    return {"mensaje": "Sancion eliminada"}


@app.get("/torneos")
def listar_torneos(_rol: str = Depends(solo_admin)):
    return fetch_all("SELECT * FROM torneo ORDER BY id_torneo")


@app.post("/torneos", dependencies=[Depends(solo_admin)])
def crear_torneo(torneo: TorneoIn):
    execute(
        "INSERT INTO torneo (nombre, anio, semestre, fecha_inicio, fecha_fin, estado) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (
            torneo.nombre,
            torneo.anio,
            torneo.semestre,
            torneo.fecha_inicio,
            torneo.fecha_fin,
            torneo.estado,
        ),
        rol="administrador",
    )
    return {"mensaje": "Torneo creado"}


@app.put("/torneos/{id_torneo}/estado", dependencies=[Depends(solo_admin)])
def actualizar_estado_torneo(id_torneo: int, datos: EstadoTorneoIn):
    torneo = fetch_one(
        "SELECT estado FROM torneo WHERE id_torneo=%s",
        (id_torneo,),
        rol="administrador",
    )
    if not torneo:
        error("Torneo inexistente")
    transiciones = {"inscripcion": "en curso", "en curso": "finalizado"}
    if datos.estado != torneo["estado"] and transiciones.get(torneo["estado"]) != datos.estado:
        error("El estado del torneo solo puede avanzar de inscripcion a en curso y luego a finalizado")
    if datos.estado == "en curso":
        equipos_invalidos = fetch_one(
            "SELECT e.id_equipo FROM equipo e "
            "LEFT JOIN equipo_jugador_torneo ejt ON ejt.id_equipo=e.id_equipo "
            "LEFT JOIN jugador j ON j.ci=ejt.ci_jugador "
            "WHERE e.id_torneo=%s "
            "GROUP BY e.id_equipo, e.ci_capitan, e.id_facultad "
            "HAVING COUNT(ejt.ci_jugador) NOT BETWEEN 5 AND 10 "
            "OR COALESCE(SUM(CASE WHEN j.tipo IN ('docente','funcionario') THEN 1 ELSE 0 END),0)>2 "
            "OR COALESCE(SUM(CASE WHEN ejt.ci_jugador=e.ci_capitan AND j.id_facultad=e.id_facultad "
            "THEN 1 ELSE 0 END),0)=0 "
            "LIMIT 1",
            (id_torneo,),
            rol="administrador",
        )
        if equipos_invalidos:
            error("Cada equipo necesita de 5 a 10 jugadores, maximo dos docentes/funcionarios y un capitan del plantel")
    execute("UPDATE torneo SET estado=%s WHERE id_torneo=%s", (datos.estado, id_torneo), rol="administrador")
    return {"mensaje": "Estado del torneo actualizado"}


@app.get("/facultades")
def listar_facultades(_rol: str = Depends(solo_admin)):
    return fetch_all("SELECT * FROM facultad ORDER BY id_facultad")


@app.get("/turnos")
def listar_turnos(_rol: str = Depends(solo_admin)):
    return fetch_all("SELECT * FROM turno ORDER BY id_turno")


# --- Reportes ---

@app.get("/partidos/{id_partido}/resultado")
def obtener_resultado_partido(id_partido: int, _rol: str = Depends(solo_admin)):
    resultado = fetch_one(
        "SELECT * FROM resultado_partido WHERE id_partido=%s",
        (id_partido,),
        rol="administrador",
    )
    if resultado:
        return resultado
    partido = fetch_one(
        "SELECT estado FROM partido WHERE id_partido=%s",
        (id_partido,),
        rol="administrador",
    )
    if not partido:
        raise HTTPException(status_code=404, detail="Partido inexistente")
    raise HTTPException(status_code=409, detail="El partido todavía no tiene resultado")


@app.get("/reportes/tabla-posiciones")
def reporte_tabla_posiciones(torneo_id: int = 1, _rol: str = Depends(solo_admin)):
    return consultas.tabla_posiciones(torneo_id)


@app.get("/reportes/goleadores")
def reporte_goleadores(torneo_id: int = 1, _rol: str = Depends(solo_admin)):
    return consultas.tabla_goleadores(torneo_id)


@app.get("/reportes/fair-play")
def reporte_fair_play(torneo_id: int = 1, _rol: str = Depends(solo_admin)):
    return consultas.fair_play_por_equipo(torneo_id)


@app.get("/reportes/promedio-goles")
def reporte_promedio_goles(torneo_id: int = 1, _rol: str = Depends(solo_admin)):
    return consultas.promedio_goles_por_fecha(torneo_id)


@app.get("/reportes/porcentaje-jugados")
def reporte_porcentaje_jugados(torneo_id: int = 1, _rol: str = Depends(solo_admin)):
    return consultas.porcentaje_partidos_jugados(torneo_id)


@app.get("/reportes/canchas-turnos")
def reporte_canchas_turnos(torneo_id: int = 1, _rol: str = Depends(solo_admin)):
    return consultas.canchas_y_turnos_mas_utilizados(torneo_id)


@app.get("/reportes/jugadores-facultad-tipo")
def reporte_jugadores_facultad_tipo(torneo_id: int = 1, _rol: str = Depends(solo_admin)):
    return consultas.jugadores_por_facultad_y_tipo(torneo_id)


@app.get("/reportes/jugadores-sin-planilla")
def reporte_jugadores_sin_planilla(torneo_id: int = 1, _rol: str = Depends(solo_admin)):
    return consultas.jugadores_que_nunca_estuvieron_en_planilla(torneo_id)


@app.get("/reportes/sanciones-equipo-motivo")
def reporte_sanciones_equipo_motivo(torneo_id: int = 1, _rol: str = Depends(solo_admin)):
    return consultas.sanciones_por_equipo_y_motivo(torneo_id)


@app.get("/reportes/jugadores-tarjetas")
def reporte_jugadores_tarjetas(torneo_id: int = 1, _rol: str = Depends(solo_admin)):
    return consultas.jugadores_con_mas_tarjetas(torneo_id)


@app.get("/reportes/riesgo-suspension")
def reporte_riesgo_suspension(torneo_id: int = 1, _rol: str = Depends(solo_admin)):
    return consultas.jugadores_en_riesgo_de_suspension(torneo_id)


@app.get("/reportes/valla-menos-vencida")
def reporte_valla_menos_vencida(torneo_id: int = 1, _rol: str = Depends(solo_admin)):
    return consultas.valla_menos_vencida(torneo_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
