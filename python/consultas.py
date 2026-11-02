"""Consultas del torneo ejecutadas mediante el módulo backend."""

from backend import fetch_all


def partidos_jugados_por_equipo(torneo_id=1):
    return fetch_all(
        """
        SELECT e.nombre AS equipo, COUNT(p.id_partido) AS partidos_jugados
        FROM equipo e
        JOIN partido p
          ON e.id_equipo = p.id_equipo_local
          OR e.id_equipo = p.id_equipo_visitante
        WHERE e.id_torneo = %s AND p.estado = 'jugado'
        GROUP BY e.id_equipo, e.nombre
        ORDER BY partidos_jugados DESC
        """,
        (torneo_id,),
    )
# El %s protege contra inyecciones sql, porque sustituye el valor del segundo parametro

def tabla_goleadores(torneo_id=1, limite=10):
    return fetch_all(
        """
        SELECT j.ci, j.nombre, j.apellido, COUNT(g.id_gol) AS cantidad_goles
        FROM gol g
        JOIN jugador j ON j.ci = g.ci_jugador
        JOIN partido p ON p.id_partido = g.id_partido
        WHERE p.id_torneo = %s AND p.estado = 'jugado' AND g.autogol = 0
        GROUP BY j.ci, j.nombre, j.apellido
        ORDER BY cantidad_goles DESC
        LIMIT %s
        """,
        (torneo_id, limite),
    )


def fair_play_por_equipo(torneo_id=1):
    return fetch_all(
        """
        SELECT e.nombre AS equipo, t.color,
               COUNT(t.id_tarjeta) AS cantidad_tarjetas
        FROM tarjeta t
        JOIN partido p ON p.id_partido = t.id_partido
        JOIN planilla_partido pp
          ON pp.id_partido = t.id_partido AND pp.ci_jugador = t.ci_jugador
        JOIN equipo e ON e.id_equipo = pp.id_equipo
        WHERE p.id_torneo = %s AND p.estado = 'jugado'
        GROUP BY e.nombre, t.color
        ORDER BY e.nombre
        """,
        (torneo_id,),
    )


def goles_por_fecha(torneo_id=1):
    return fetch_all(
        """
        SELECT p.numero_fecha, COUNT(g.id_gol) AS cantidad_goles,
               COUNT(DISTINCT p.id_partido) AS partidos_jugados
        FROM partido p
        LEFT JOIN gol g ON g.id_partido = p.id_partido
        WHERE p.id_torneo = %s AND p.estado = 'jugado'
        GROUP BY p.numero_fecha
        ORDER BY p.numero_fecha
        """,
        (torneo_id,),
    )


def canchas_y_turnos_mas_utilizados(torneo_id=1):
    return fetch_all(
        """
        SELECT c.nombre_cancha, co.nombre AS complejo,
               t.hora_inicio, t.hora_fin,
               COUNT(p.id_partido) AS cantidad_partidos
        FROM partido p
        JOIN cancha c
          ON c.nombre_cancha = p.nombre_cancha AND c.id_complejo = p.id_complejo
        JOIN complejo co ON co.id_complejo = c.id_complejo
        JOIN turno t ON t.id_turno = p.id_turno
        WHERE p.id_torneo = %s AND p.estado = 'jugado'
        GROUP BY c.nombre_cancha, co.nombre, t.hora_inicio, t.hora_fin
        ORDER BY cantidad_partidos DESC
        """,
        (torneo_id,),
    )


def jugadores_por_facultad_y_tipo(torneo_id=1):
    return fetch_all(
        """
        SELECT f.nombre AS facultad, j.tipo,
               COUNT(j.ci) AS cantidad_jugadores
        FROM jugador j
        JOIN facultad f ON f.id_facultad = j.id_facultad
        JOIN equipo_jugador_torneo ejt ON ejt.ci_jugador = j.ci
        WHERE ejt.id_torneo = %s
        GROUP BY f.nombre, j.tipo
        ORDER BY f.nombre, j.tipo
        """,
        (torneo_id,),
    )


def jugadores_que_nunca_estuvieron_en_planilla(torneo_id=1):
    return fetch_all(
        """
        SELECT j.ci, j.nombre, j.apellido, e.nombre AS equipo
        FROM equipo_jugador_torneo ejt
        JOIN jugador j ON j.ci = ejt.ci_jugador
        JOIN equipo e ON e.id_equipo = ejt.id_equipo
        LEFT JOIN planilla_partido pp
          ON pp.ci_jugador = ejt.ci_jugador AND pp.id_equipo = ejt.id_equipo
        WHERE ejt.id_torneo = %s AND pp.ci_jugador IS NULL
        """,
        (torneo_id,),
    )


def sanciones_por_equipo_y_motivo(torneo_id=1):
    return fetch_all(
        """
        SELECT e.nombre AS equipo, sj.motivo,
               COUNT(sj.id_sancion) AS cantidad_sanciones
        FROM sancion_jugador sj
        JOIN equipo_jugador_torneo ejt
          ON ejt.ci_jugador = sj.ci_jugador AND ejt.id_torneo = sj.id_torneo
        JOIN equipo e ON e.id_equipo = ejt.id_equipo
        WHERE sj.id_torneo = %s
        GROUP BY e.nombre, sj.motivo
        ORDER BY e.nombre
        """,
        (torneo_id,),
    )


def partidos_por_estado(torneo_id=1):
    return fetch_all(
        """
        SELECT p.estado, COUNT(p.id_partido) AS cantidad_partidos
        FROM partido p
        WHERE p.id_torneo = %s
        GROUP BY p.estado
        ORDER BY cantidad_partidos DESC
        """,
        (torneo_id,),
    )


def jugadores_con_mas_tarjetas(torneo_id=1):
    return fetch_all(
        """
        SELECT j.ci, j.nombre, j.apellido,
               COUNT(t.id_tarjeta) AS cantidad_tarjetas
        FROM tarjeta t
        JOIN jugador j ON j.ci = t.ci_jugador
        JOIN partido p ON p.id_partido = t.id_partido
        WHERE p.id_torneo = %s AND p.estado = 'jugado'
        GROUP BY j.ci, j.nombre, j.apellido
        ORDER BY cantidad_tarjetas DESC
        """,
        (torneo_id,),
    )


def partidos_disputados_por_fecha(torneo_id=1):
    return fetch_all(
        """
        SELECT p.numero_fecha, COUNT(p.id_partido) AS cantidad_partidos
        FROM partido p
        WHERE p.id_torneo = %s AND p.estado = 'jugado'
        GROUP BY p.numero_fecha
        ORDER BY p.numero_fecha
        """,
        (torneo_id,),
    )


def jugadores_por_equipo(torneo_id=1):
    return fetch_all(
        """
        SELECT e.nombre AS equipo,
               COUNT(ejt.ci_jugador) AS cantidad_jugadores
        FROM equipo e
        JOIN equipo_jugador_torneo ejt ON ejt.id_equipo = e.id_equipo
        WHERE e.id_torneo = %s
        GROUP BY e.id_equipo, e.nombre
        ORDER BY cantidad_jugadores DESC
        """,
        (torneo_id,),
    )


def todas_las_consultas(torneo_id=1):
    """Ejecuta y devuelve todas las consultas agrupadas por nombre."""
    return {
        "partidos_jugados_por_equipo": partidos_jugados_por_equipo(torneo_id),
        "tabla_goleadores": tabla_goleadores(torneo_id),
        "fair_play_por_equipo": fair_play_por_equipo(torneo_id),
        "goles_por_fecha": goles_por_fecha(torneo_id),
        "canchas_y_turnos_mas_utilizados": canchas_y_turnos_mas_utilizados(torneo_id),
        "jugadores_por_facultad_y_tipo": jugadores_por_facultad_y_tipo(torneo_id),
        "jugadores_que_nunca_estuvieron_en_planilla":
            jugadores_que_nunca_estuvieron_en_planilla(torneo_id),
        "sanciones_por_equipo_y_motivo": sanciones_por_equipo_y_motivo(torneo_id),
        "partidos_por_estado": partidos_por_estado(torneo_id),
        "jugadores_con_mas_tarjetas": jugadores_con_mas_tarjetas(torneo_id),
        "partidos_disputados_por_fecha": partidos_disputados_por_fecha(torneo_id),
        "jugadores_por_equipo": jugadores_por_equipo(torneo_id),
    }


if __name__ == "__main__":
    import pprint

    pprint.pp(todas_las_consultas())
