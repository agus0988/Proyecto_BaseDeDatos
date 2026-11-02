USE torneo_futbol5;

INSERT INTO login (correo, contrasena, rol) VALUES
('admin@ucu.edu.uy', SHA2('admin123', 256), 'administrador'),
('planillero@ucu.edu.uy', SHA2('planillero123', 256), 'planillero');

CREATE VIEW resultado_partido AS
SELECT p.id_partido, p.id_torneo, p.numero_fecha,
       p.id_equipo_local, p.id_equipo_visitante,
       (SELECT COUNT(*) FROM gol g
        JOIN planilla_partido pp ON pp.id_partido = g.id_partido AND pp.ci_jugador = g.ci_jugador
        WHERE g.id_partido = p.id_partido
          AND ((pp.id_equipo = p.id_equipo_local AND g.autogol = 0)
            OR (pp.id_equipo = p.id_equipo_visitante AND g.autogol = 1))) AS goles_local,
       (SELECT COUNT(*) FROM gol g
        JOIN planilla_partido pp ON pp.id_partido = g.id_partido AND pp.ci_jugador = g.ci_jugador
        WHERE g.id_partido = p.id_partido
          AND ((pp.id_equipo = p.id_equipo_visitante AND g.autogol = 0)
            OR (pp.id_equipo = p.id_equipo_local AND g.autogol = 1))) AS goles_visitante
FROM partido p
WHERE p.estado = 'jugado';

GRANT SELECT ON torneo_futbol5.resultado_partido TO 'planillero_torneo'@'%';
