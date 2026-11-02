import pytest

import consultas


CONSULTAS = [
    "tabla_goleadores",
    "fair_play_por_equipo",
    "jugadores_por_facultad_y_tipo",
    "jugadores_que_nunca_estuvieron_en_planilla",
    "sanciones_por_equipo_y_motivo",
    "jugadores_con_mas_tarjetas",
    "tabla_posiciones",
    "promedio_goles_por_fecha",
    "porcentaje_partidos_jugados",
    "jugadores_en_riesgo_de_suspension",
    "valla_menos_vencida",
]


@pytest.mark.parametrize("nombre", CONSULTAS)
def test_consulta_usa_el_id_del_torneo(monkeypatch, nombre):
    llamadas = []

    def fake_fetch_all(sql, params):
        llamadas.append((sql, params))
        return [{"ok": True}]

    monkeypatch.setattr(consultas, "fetch_all", fake_fetch_all)

    resultado = getattr(consultas, nombre)(torneo_id=4)

    assert resultado == [{"ok": True}]
    assert llamadas
    assert llamadas[0][1][0] == 4
    assert "%s" in llamadas[0][0]


def test_tabla_goleadores_envia_el_limite(monkeypatch):
    llamada = {}

    def fake_fetch_all(sql, params):
        llamada["params"] = params
        return []

    monkeypatch.setattr(consultas, "fetch_all", fake_fetch_all)

    consultas.tabla_goleadores(torneo_id=2, limite=5)

    assert llamada["params"] == (2, 5)


def test_todas_las_consultas_devuelve_los_12_reportes(monkeypatch):
    monkeypatch.setattr(consultas, "fetch_all", lambda sql, params: [])

    resultado = consultas.todas_las_consultas(1)

    assert len(resultado) == 12
    assert "tabla_goleadores" in resultado
    assert "jugadores_en_riesgo_de_suspension" in resultado


def test_canchas_y_turnos_devuelve_dos_rankings_independientes(monkeypatch):
    llamadas = []

    def fake_fetch_all(sql, params):
        llamadas.append((sql, params))
        return [{"ok": True}]

    monkeypatch.setattr(consultas, "fetch_all", fake_fetch_all)

    resultado = consultas.canchas_y_turnos_mas_utilizados(torneo_id=4)

    assert resultado == {"canchas": [{"ok": True}], "turnos": [{"ok": True}]}
    assert len(llamadas) == 2
    assert all(params == (4,) for _, params in llamadas)
    assert "GROUP BY c.id_complejo, c.nombre_cancha" in llamadas[0][0]
    assert "GROUP BY t.id_turno" in llamadas[1][0]


def test_tabla_posiciones_parte_de_equipo_para_incluir_los_sin_partidos(monkeypatch):
    llamada = {}

    def fake_fetch_all(sql, params):
        llamada["sql"] = sql
        llamada["params"] = params
        return [{"equipo": f"Equipo {numero}"} for numero in range(1, 7)]

    monkeypatch.setattr(consultas, "fetch_all", fake_fetch_all)

    resultado = consultas.tabla_posiciones(torneo_id=3)

    assert len(resultado) == 6
    assert "FROM equipo e" in llamada["sql"]
    assert "LEFT JOIN (" in llamada["sql"]
    assert llamada["params"] == (3,)
