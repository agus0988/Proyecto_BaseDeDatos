from datetime import date

import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture
def client():
    api.app.dependency_overrides.clear()
    with TestClient(api.app) as test_client:
        yield test_client
    api.app.dependency_overrides.clear()


def autenticar_como(rol):
    api.app.dependency_overrides[api.usuario_actual] = lambda: rol


def test_credenciales_invalidas_devuelven_401(client, monkeypatch):
    monkeypatch.setattr(api, "fetch_one", lambda *args, **kwargs: None)

    respuesta = client.get("/jugadores", auth=("incorrecto", "incorrecta"))

    assert respuesta.status_code == 401


def test_planillero_no_puede_crear_jugadores(client):
    autenticar_como("planillero")

    respuesta = client.post(
        "/jugadores",
        json={
            "ci": "1234567",
            "nombre": "Ana",
            "apellido": "Perez",
            "email": "ana@example.com",
            "fecha_nacimiento": "2000-01-01",
            "id_facultad": 1,
            "tipo": "grado",
        },
    )

    assert respuesta.status_code == 403


def test_payload_de_complejo_invalido_devuelve_422(client):
    autenticar_como("administrador")

    respuesta = client.post("/complejos", json={"nombre": "Complejo"})

    assert respuesta.status_code == 422


def test_partido_rechaza_cancha_ocupada(client, monkeypatch):
    autenticar_como("administrador")

    def fake_fetch_one(sql, params=(), rol="administrador"):
        if "SELECT COUNT(*) AS n FROM equipo WHERE" in sql:
            return {"n": 2}
        if "SELECT COUNT(*) AS n FROM equipo_jugador_torneo" in sql:
            return {"n": 5}
        if "AND dia=%s AND id_turno=%s" in sql:
            return {"ok": 1}
        return None

    monkeypatch.setattr(api, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(api, "execute", lambda *args, **kwargs: pytest.fail("No debe guardar el partido"))

    respuesta = client.post(
        "/partidos",
        json={
            "id_torneo": 1,
            "numero_fecha": 1,
            "id_equipo_local": 1,
            "id_equipo_visitante": 2,
            "dia": "2026-03-01",
            "id_turno": 1,
            "nombre_cancha": "Cancha A",
            "id_complejo": 1,
        },
    )

    assert respuesta.status_code == 400
    assert "ocupada" in respuesta.json()["detail"]


def test_no_se_agrega_jugador_de_otra_facultad(client, monkeypatch):
    autenticar_como("administrador")

    def fake_fetch_one(sql, params=(), rol="administrador"):
        if "SELECT e.id_facultad, t.estado" in sql:
            return {"id_facultad": 1, "estado": "inscripcion"}
        if "SELECT id_facultad, tipo FROM jugador" in sql:
            return {"id_facultad": 2, "tipo": "grado"}
        pytest.fail(f"Consulta inesperada: {sql}")

    monkeypatch.setattr(api, "fetch_one", fake_fetch_one)

    respuesta = client.post(
        "/equipos/1/jugadores",
        json={"ci_jugador": "1234567", "numero_camiseta": 7},
    )

    assert respuesta.status_code == 400
    assert "otra facultad" in respuesta.json()["detail"]


def test_se_rechaza_el_jugador_11_del_plantel(client, monkeypatch):
    autenticar_como("administrador")

    def fake_fetch_one(sql, params=(), rol="administrador"):
        if "SELECT e.id_facultad, t.estado" in sql:
            return {"id_facultad": 1, "estado": "inscripcion"}
        if "SELECT id_facultad, tipo FROM jugador" in sql:
            return {"id_facultad": 1, "tipo": "grado"}
        if "SELECT COUNT(*) AS total" in sql:
            return {"total": 10, "staff": 0}
        pytest.fail(f"Consulta inesperada: {sql}")

    monkeypatch.setattr(api, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(api, "execute", lambda *args, **kwargs: pytest.fail("No debe agregar el jugador 11"))

    respuesta = client.post(
        "/equipos/1/jugadores",
        json={"ci_jugador": "1234567", "numero_camiseta": 7},
    )

    assert respuesta.status_code == 400
    assert "10 jugadores" in respuesta.json()["detail"]


def test_planilla_rechaza_jugador_suspendido(client, monkeypatch):
    autenticar_como("planillero")

    def fake_fetch_one(sql, params=(), rol="administrador"):
        if "SELECT p.id_torneo, p.numero_fecha, p.estado" in sql:
            return {
                "id_torneo": 1,
                "numero_fecha": 3,
                "estado": "jugado",
                "id_equipo_local": 1,
                "id_equipo_visitante": 2,
                "turno_finalizado": 1,
            }
        if "SELECT 1 AS ok FROM equipo_jugador_torneo WHERE id_equipo=%s" in sql:
            return {"ok": 1}
        if "FROM sancion_jugador" in sql:
            return {"ok": 1}
        pytest.fail(f"Consulta inesperada: {sql}")

    monkeypatch.setattr(api, "fetch_one", fake_fetch_one)

    respuesta = client.post(
        "/partidos/10/planilla",
        json={"ci_jugador": "1234567", "id_equipo": 1},
    )

    assert respuesta.status_code == 400
    assert "suspendido" in respuesta.json()["detail"]


def test_tarjeta_roja_genera_sancion(client, monkeypatch):
    autenticar_como("planillero")
    ejecuciones = []

    def fake_fetch_one(sql, params=(), rol="administrador"):
        if "FROM partido p JOIN turno t" in sql:
            return {"estado": "jugado", "vencido": 0}
        if "SELECT id_torneo, numero_fecha FROM partido" in sql:
            return {"id_torneo": 1, "numero_fecha": 3}
        pytest.fail(f"Consulta inesperada: {sql}")

    def fake_execute(sql, params=(), rol="administrador"):
        ejecuciones.append((sql, params, rol))

    monkeypatch.setattr(api, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(api, "execute", fake_execute)

    respuesta = client.post(
        "/partidos/10/tarjetas",
        json={"ci_jugador": "1234567", "minuto": 45, "color": "roja"},
    )

    assert respuesta.status_code == 200
    assert any("INSERT INTO sancion_jugador" in sql and params[2] == "roja"
               for sql, params, _ in ejecuciones)


@pytest.mark.parametrize(
    ("ruta", "id_objeto"),
    [
        ("/partidos/10/planilla/1234567", None),
        ("/partidos/10/goles/21", 21),
        ("/partidos/10/tarjetas/31", 31),
    ],
)
def test_planillero_elimina_eventos_con_su_rol(client, monkeypatch, ruta, id_objeto):
    autenticar_como("planillero")
    ejecuciones = []
    monkeypatch.setattr(
        api,
        "fetch_one",
        lambda *args, **kwargs: {"estado": "programado", "vencido": 0},
    )
    monkeypatch.setattr(
        api,
        "execute",
        lambda sql, params=(), rol="administrador": ejecuciones.append((sql, params, rol)),
    )

    respuesta = client.delete(ruta)

    assert respuesta.status_code == 200
    assert len(ejecuciones) == 1
    assert ejecuciones[0][2] == "planillero"
    if id_objeto is not None:
        assert ejecuciones[0][1] == (id_objeto, 10)


def test_reporte_de_posiciones_devuelve_seis_equipos(client, monkeypatch):
    autenticar_como("administrador")
    filas = [{"equipo": f"Equipo {numero}"} for numero in range(1, 7)]
    monkeypatch.setattr(api.consultas, "tabla_posiciones", lambda torneo_id: filas)

    respuesta = client.get("/reportes/tabla-posiciones?torneo_id=1")

    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 6


def test_api_expone_los_18_reportes():
    rutas = {
        ruta.path
        for ruta in api.app.routes
        if ruta.path.startswith("/reportes/")
    }

    assert len(rutas) == 18
    assert "/reportes/goles-por-fecha" in rutas


def test_no_se_permite_actualizar_partido_jugado_fuera_de_48_horas(client, monkeypatch):
    autenticar_como("administrador")
    monkeypatch.setattr(
        api,
        "fetch_one",
        lambda *args, **kwargs: {"estado": "jugado", "vencido": 1},
    )
    monkeypatch.setattr(api, "execute", lambda *args, **kwargs: pytest.fail("No debe modificar el partido"))

    respuesta = client.put(
        "/partidos/10",
        json={
            "id_torneo": 1,
            "numero_fecha": 1,
            "id_equipo_local": 1,
            "id_equipo_visitante": 2,
            "dia": date.today().isoformat(),
            "id_turno": 1,
            "nombre_cancha": "Cancha A",
            "id_complejo": 1,
        },
    )

    assert respuesta.status_code == 400
    assert "48 horas" in respuesta.json()["detail"]
