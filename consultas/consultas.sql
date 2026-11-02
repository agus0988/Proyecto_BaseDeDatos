USE torneo_futbol5;

-- 1. Tabla de posiciones (incluye equipos sin partidos jugados)
SELECT
    e.nombre AS equipo,
    COUNT(r.id_partido) AS pj,
    COALESCE(SUM(r.gf > r.gc), 0) AS pg,
    COALESCE(SUM(r.gf = r.gc), 0) AS pe,
    COALESCE(SUM(r.gf < r.gc), 0) AS pp,
    COALESCE(SUM(r.gf), 0) AS gf,
    COALESCE(SUM(r.gc), 0) AS gc,
    COALESCE(SUM(r.gf - r.gc), 0) AS dg,
    COALESCE(SUM(CASE
        WHEN r.gf > r.gc THEN 3
        WHEN r.gf = r.gc THEN 1
        ELSE 0
    END), 0) AS puntos
FROM equipo e
LEFT JOIN (
    SELECT id_partido, id_torneo, id_equipo_local AS id_equipo,
           goles_local AS gf, goles_visitante AS gc
    FROM resultado_partido
    UNION ALL
    SELECT id_partido, id_torneo, id_equipo_visitante,
           goles_visitante, goles_local
    FROM resultado_partido
) r ON r.id_torneo = e.id_torneo AND r.id_equipo = e.id_equipo
WHERE e.id_torneo = 1
GROUP BY e.id_equipo, e.nombre
ORDER BY puntos DESC, dg DESC, gf DESC;

-- 2. Tabla de goleadores (10 jugadores)
SELECT j.ci, j.nombre, j.apellido, COUNT(g.id_gol) AS cantidad_goles
FROM gol g
JOIN jugador j ON j.ci = g.ci_jugador
JOIN partido p ON p.id_partido = g.id_partido
WHERE p.id_torneo = 1 AND p.estado = 'jugado' AND g.autogol = 0
GROUP BY j.ci, j.nombre, j.apellido
ORDER BY cantidad_goles DESC
LIMIT 10;

-- 3. Fair play por equipo (amarilla = 1 punto, roja = 3 puntos)
SELECT
    e.nombre AS equipo,
    COALESCE(SUM(t.color = 'amarilla'), 0) AS tarjetas_amarillas,
    COALESCE(SUM(t.color = 'roja'), 0) AS tarjetas_rojas,
    COALESCE(SUM(CASE t.color
        WHEN 'amarilla' THEN 1
        WHEN 'roja' THEN 3
        ELSE 0
    END), 0) AS puntos_fair_play
FROM equipo e
LEFT JOIN partido p
    ON p.id_torneo = e.id_torneo
    AND (p.id_equipo_local = e.id_equipo OR p.id_equipo_visitante = e.id_equipo)
LEFT JOIN planilla_partido pp
    ON pp.id_partido = p.id_partido AND pp.id_equipo = e.id_equipo
LEFT JOIN tarjeta t
    ON t.id_partido = pp.id_partido AND t.ci_jugador = pp.ci_jugador
WHERE e.id_torneo = 1
GROUP BY e.id_equipo, e.nombre
ORDER BY puntos_fair_play, e.nombre;

-- 4. Promedio de goles por fecha y promedio total
SELECT numero_fecha,
       ROUND(AVG(goles_local + goles_visitante), 2) AS promedio_goles
FROM resultado_partido
WHERE id_torneo = 1
GROUP BY numero_fecha WITH ROLLUP;

-- 5. Rankings independientes de canchas y turnos más utilizados
SELECT c.nombre_cancha, co.nombre AS complejo,
       COUNT(p.id_partido) AS cantidad_partidos
FROM partido p
JOIN cancha c
    ON c.nombre_cancha = p.nombre_cancha AND c.id_complejo = p.id_complejo
JOIN complejo co ON co.id_complejo = c.id_complejo
WHERE p.id_torneo = 1 AND p.estado = 'jugado'
GROUP BY c.id_complejo, c.nombre_cancha, co.nombre
ORDER BY cantidad_partidos DESC, co.nombre, c.nombre_cancha;

SELECT t.id_turno, t.hora_inicio, t.hora_fin,
       COUNT(p.id_partido) AS cantidad_partidos
FROM partido p
JOIN turno t ON t.id_turno = p.id_turno
WHERE p.id_torneo = 1 AND p.estado = 'jugado'
GROUP BY t.id_turno, t.hora_inicio, t.hora_fin
ORDER BY cantidad_partidos DESC, t.hora_inicio;

-- 6. Jugadores por facultad y tipo
SELECT f.nombre AS facultad, j.tipo, COUNT(j.ci) AS cantidad_jugadores
FROM jugador j
JOIN facultad f ON f.id_facultad = j.id_facultad
JOIN equipo_jugador_torneo ejt ON ejt.ci_jugador = j.ci
WHERE ejt.id_torneo = 1
GROUP BY f.nombre, j.tipo
ORDER BY f.nombre, j.tipo;

-- 7. Jugadores inscritos que nunca estuvieron en una planilla
SELECT j.ci, j.nombre, j.apellido, e.nombre AS equipo
FROM equipo_jugador_torneo ejt
JOIN jugador j ON j.ci = ejt.ci_jugador
JOIN equipo e ON e.id_equipo = ejt.id_equipo
LEFT JOIN planilla_partido pp
    ON pp.ci_jugador = ejt.ci_jugador AND pp.id_equipo = ejt.id_equipo
WHERE ejt.id_torneo = 1 AND pp.ci_jugador IS NULL;

-- 8. Cantidad de sanciones por equipo y motivo
SELECT e.nombre AS equipo, sj.motivo,
       COUNT(sj.id_sancion) AS cantidad_sanciones
FROM sancion_jugador sj
JOIN equipo_jugador_torneo ejt
    ON ejt.ci_jugador = sj.ci_jugador AND ejt.id_torneo = sj.id_torneo
JOIN equipo e ON e.id_equipo = ejt.id_equipo
WHERE sj.id_torneo = 1
GROUP BY e.nombre, sj.motivo
ORDER BY e.nombre, sj.motivo;

-- 9. Porcentaje de partidos jugados, postergados y cancelados
SELECT
    COALESCE(ROUND(100 * SUM(estado = 'jugado') / NULLIF(COUNT(*), 0), 1), 0)
        AS pct_jugados,
    COALESCE(ROUND(100 * SUM(estado IN ('postergado','cancelado')) /
        NULLIF(COUNT(*), 0), 1), 0) AS pct_postergados_cancelados
FROM partido
WHERE id_torneo = 1;

-- 10. Jugadores a una tarjeta amarilla de la suspensión por acumulación
SELECT t.ci_jugador, j.nombre, j.apellido,
       COUNT(*) AS amarillas, MAX(p.numero_fecha) AS ultima_fecha
FROM tarjeta t
JOIN partido p ON p.id_partido = t.id_partido
JOIN jugador j ON j.ci = t.ci_jugador
WHERE p.id_torneo = 1 AND t.color = 'amarilla'
GROUP BY t.ci_jugador, j.nombre, j.apellido
HAVING COUNT(*) = 2
ORDER BY amarillas DESC;

-- 11. Valla menos vencida
SELECT equipo, SUM(goles_recibidos) AS goles_en_contra
FROM (
    SELECT e.nombre AS equipo, r.goles_visitante AS goles_recibidos
    FROM resultado_partido r
    JOIN equipo e ON e.id_equipo = r.id_equipo_local
    WHERE r.id_torneo = 1
    UNION ALL
    SELECT e.nombre AS equipo, r.goles_local AS goles_recibidos
    FROM resultado_partido r
    JOIN equipo e ON e.id_equipo = r.id_equipo_visitante
    WHERE r.id_torneo = 1
) sub
GROUP BY equipo
ORDER BY goles_en_contra, equipo;

-- 12. Jugadores con más tarjetas
SELECT j.ci, j.nombre, j.apellido, COUNT(t.id_tarjeta) AS cantidad_tarjetas
FROM tarjeta t
JOIN jugador j ON j.ci = t.ci_jugador
JOIN partido p ON p.id_partido = t.id_partido
WHERE p.id_torneo = 1 AND p.estado = 'jugado'
GROUP BY j.ci, j.nombre, j.apellido
ORDER BY cantidad_tarjetas DESC;
