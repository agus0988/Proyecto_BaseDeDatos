USE torneo_futbol5;

-- 1. Partidos jugados por equipo

SELECT
    e.nombre AS equipo,
    COUNT(p.id_partido) AS partidos_jugados
FROM equipo e
JOIN partido p
    ON e.id_equipo = p.id_equipo_local
    OR e.id_equipo = p.id_equipo_visitante
WHERE e.id_torneo = 1
AND p.estado = 'jugado'
GROUP BY e.id_equipo, e.nombre
ORDER BY partidos_jugados DESC;


-- 2. Tabla de goleadores (10 jugadores)

SELECT
    j.ci,
    j.nombre,
    j.apellido,
    COUNT(g.id_gol) AS cantidad_goles
FROM gol g
JOIN jugador j ON j.ci = g.ci_jugador
JOIN partido p ON p.id_partido = g.id_partido
WHERE p.id_torneo = 1
AND p.estado = 'jugado'
AND g.autogol = 0
GROUP BY j.ci, j.nombre, j.apellido
ORDER BY cantidad_goles DESC
LIMIT 10;


-- 3. Fair play por equipo

SELECT
    e.nombre AS equipo,
    t.color,
    COUNT(t.id_tarjeta) AS cantidad_tarjetas
FROM tarjeta t
JOIN partido p ON p.id_partido = t.id_partido
JOIN planilla_partido pp
    ON pp.id_partido = t.id_partido
    AND pp.ci_jugador = t.ci_jugador
JOIN equipo e ON e.id_equipo = pp.id_equipo
WHERE p.id_torneo = 1
AND p.estado = 'jugado'
GROUP BY e.nombre, t.color
ORDER BY e.nombre;


-- 4. Goles por fecha

SELECT
    p.numero_fecha,
    COUNT(g.id_gol) AS cantidad_goles,
    COUNT(DISTINCT p.id_partido) AS partidos_jugados
FROM partido p
LEFT JOIN gol g ON g.id_partido = p.id_partido
WHERE p.id_torneo = 1
AND p.estado = 'jugado'
GROUP BY p.numero_fecha
ORDER BY p.numero_fecha;


-- 5. Canchas y turnos más utilizados

SELECT
    c.nombre_cancha,
    co.nombre AS complejo,
    t.hora_inicio,
    t.hora_fin,
    COUNT(p.id_partido) AS cantidad_partidos
FROM partido p
JOIN cancha c
    ON c.nombre_cancha = p.nombre_cancha
    AND c.id_complejo = p.id_complejo
JOIN complejo co ON co.id_complejo = c.id_complejo
JOIN turno t ON t.id_turno = p.id_turno
WHERE p.id_torneo = 1
AND p.estado = 'jugado'
GROUP BY c.nombre_cancha, co.nombre, t.hora_inicio, t.hora_fin
ORDER BY cantidad_partidos DESC;


-- 6. Jugadores por facultad y tipo

SELECT
    f.nombre AS facultad,
    j.tipo,
    COUNT(j.ci) AS cantidad_jugadores
FROM jugador j
JOIN facultad f ON f.id_facultad = j.id_facultad
JOIN equipo_jugador_torneo ejt ON ejt.ci_jugador = j.ci
WHERE ejt.id_torneo = 1
GROUP BY f.nombre, j.tipo
ORDER BY f.nombre, j.tipo;


-- 7. Jugadores que nunca estuvieron en una planilla

SELECT
    j.ci,
    j.nombre,
    j.apellido,
    e.nombre AS equipo
FROM equipo_jugador_torneo ejt
JOIN jugador j ON j.ci = ejt.ci_jugador
JOIN equipo e ON e.id_equipo = ejt.id_equipo
LEFT JOIN planilla_partido pp
    ON pp.ci_jugador = ejt.ci_jugador
    AND pp.id_equipo = ejt.id_equipo
WHERE ejt.id_torneo = 1
AND pp.ci_jugador IS NULL;


-- 8. Cantidad de sanciones por equipo y motivo

SELECT
    e.nombre AS equipo,
    sj.motivo,
    COUNT(sj.id_sancion) AS cantidad_sanciones
FROM sancion_jugador sj
JOIN equipo_jugador_torneo ejt
    ON ejt.ci_jugador = sj.ci_jugador
    AND ejt.id_torneo = sj.id_torneo
JOIN equipo e ON e.id_equipo = ejt.id_equipo
WHERE sj.id_torneo = 1
GROUP BY e.nombre, sj.motivo
ORDER BY e.nombre;


-- 9. Cantidad de partidos por estado

SELECT
    p.estado,
    COUNT(p.id_partido) AS cantidad_partidos
FROM partido p
WHERE p.id_torneo = 1
GROUP BY p.estado
ORDER BY cantidad_partidos DESC;


-- 10. Jugadores con más tarjetas

SELECT
    j.ci,
    j.nombre,
    j.apellido,
    COUNT(t.id_tarjeta) AS cantidad_tarjetas
FROM tarjeta t
JOIN jugador j ON j.ci = t.ci_jugador
JOIN partido p ON p.id_partido = t.id_partido
WHERE p.id_torneo = 1
AND p.estado = 'jugado'
GROUP BY j.ci, j.nombre, j.apellido
ORDER BY cantidad_tarjetas DESC;


-- 11. Partidos disputados por fecha

SELECT
    p.numero_fecha,
    COUNT(p.id_partido) AS cantidad_partidos
FROM partido p
WHERE p.id_torneo = 1
AND p.estado = 'jugado'
GROUP BY p.numero_fecha
ORDER BY p.numero_fecha;


-- 12. Cantidad de jugadores por equipo

SELECT
    e.nombre AS equipo,
    COUNT(ejt.ci_jugador) AS cantidad_jugadores
FROM equipo e
JOIN equipo_jugador_torneo ejt
    ON ejt.id_equipo = e.id_equipo
WHERE e.id_torneo = 1
GROUP BY e.id_equipo, e.nombre
ORDER BY cantidad_jugadores DESC;