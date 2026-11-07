DROP DATABASE IF EXISTS torneo_futbol5;
CREATE DATABASE torneo_futbol5;
USE torneo_futbol5;

CREATE TABLE login (
    correo VARCHAR(100) PRIMARY KEY,
    contrasena VARCHAR(255) NOT NULL,
    rol ENUM('administrador','planillero') NOT NULL,
    CHECK (correo LIKE '%_@_%._%'),
    CHECK (CHAR_LENGTH(TRIM(contrasena)) > 0)
);

CREATE TABLE facultad (
    id_facultad INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    CHECK (CHAR_LENGTH(TRIM(nombre)) > 0)
);

CREATE TABLE jugador (
    ci VARCHAR(15) PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    apellido VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    fecha_nacimiento DATE NOT NULL,
    id_facultad INT NOT NULL,
    tipo ENUM('grado','posgrado','docente','funcionario') NOT NULL,
    CHECK (ci REGEXP '^[0-9]{6,8}$'),
    CHECK (email LIKE '%_@_%._%'),
    CHECK (CHAR_LENGTH(TRIM(nombre)) > 0),
    CHECK (CHAR_LENGTH(TRIM(apellido)) > 0),
    FOREIGN KEY (id_facultad) REFERENCES facultad(id_facultad)
);

CREATE TABLE torneo (
    id_torneo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    anio INT NOT NULL,
    semestre INT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    estado ENUM('inscripcion','en curso','finalizado') NOT NULL DEFAULT 'inscripcion',
    UNIQUE (anio, semestre),
    CHECK (semestre IN (1, 2)),
    CHECK (CHAR_LENGTH(TRIM(nombre)) > 0),
    CHECK (fecha_fin >= fecha_inicio)
);

CREATE TABLE equipo (
    id_equipo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    id_torneo INT NOT NULL,
    id_facultad INT NOT NULL,
    ci_capitan VARCHAR(15),
    UNIQUE (id_equipo, id_torneo),
    UNIQUE (id_torneo, nombre),
    FOREIGN KEY (id_torneo) REFERENCES torneo(id_torneo),
    FOREIGN KEY (id_facultad) REFERENCES facultad(id_facultad),
    FOREIGN KEY (ci_capitan) REFERENCES jugador(ci),
    CHECK (CHAR_LENGTH(TRIM(nombre)) > 0)
);

CREATE TABLE equipo_jugador_torneo (
    id_equipo INT NOT NULL,
    ci_jugador VARCHAR(15) NOT NULL,
    id_torneo INT NOT NULL,
    numero_camiseta INT NOT NULL,
    PRIMARY KEY (id_equipo, ci_jugador, id_torneo),
    UNIQUE (ci_jugador, id_torneo),
    UNIQUE (id_equipo, ci_jugador),
    UNIQUE (id_equipo, numero_camiseta),
    FOREIGN KEY (id_equipo, id_torneo) REFERENCES equipo(id_equipo, id_torneo),
    FOREIGN KEY (ci_jugador) REFERENCES jugador(ci),
    CHECK (numero_camiseta BETWEEN 1 AND 99)
);

CREATE TABLE complejo (
    id_complejo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    direccion VARCHAR(150) NOT NULL,
    departamento VARCHAR(50) NOT NULL,
    CHECK (CHAR_LENGTH(TRIM(nombre)) > 0),
    CHECK (CHAR_LENGTH(TRIM(direccion)) > 0),
    CHECK (CHAR_LENGTH(TRIM(departamento)) > 0)
);

CREATE TABLE cancha (
    nombre_cancha VARCHAR(50) NOT NULL,
    id_complejo INT NOT NULL,
    superficie ENUM('sintetico','parquet') NOT NULL,
    techada BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (nombre_cancha, id_complejo),
    FOREIGN KEY (id_complejo) REFERENCES complejo(id_complejo),
    CHECK (CHAR_LENGTH(TRIM(nombre_cancha)) > 0),
    CHECK (techada IN (0, 1))
);

CREATE TABLE turno (
    id_turno INT AUTO_INCREMENT PRIMARY KEY,
    hora_inicio TIME NOT NULL UNIQUE,
    hora_fin TIME NOT NULL,
    CHECK (hora_fin > hora_inicio),
    CHECK (hora_inicio >= '18:00:00' AND hora_inicio < '23:00:00'),
    CHECK (TIMESTAMPDIFF(MINUTE, hora_inicio, hora_fin) = 60)
);

CREATE TABLE partido (
    id_partido INT AUTO_INCREMENT PRIMARY KEY,
    id_torneo INT NOT NULL,
    numero_fecha INT NOT NULL,
    id_equipo_local INT NOT NULL,
    id_equipo_visitante INT NOT NULL,
    dia DATE NOT NULL,
    id_turno INT NOT NULL,
    nombre_cancha VARCHAR(50) NOT NULL,
    id_complejo INT NOT NULL,
    estado ENUM('programado','jugado','postergado','cancelado') NOT NULL DEFAULT 'programado',
    slot_activo INT GENERATED ALWAYS AS (
        CASE WHEN estado = 'cancelado' THEN NULL ELSE 1 END
    ) STORED,
    UNIQUE (dia, id_turno, nombre_cancha, id_complejo, slot_activo),
    CHECK (numero_fecha > 0),
    CHECK (CHAR_LENGTH(TRIM(nombre_cancha)) > 0),
    FOREIGN KEY (id_equipo_local, id_torneo) REFERENCES equipo(id_equipo, id_torneo),
    FOREIGN KEY (id_equipo_visitante, id_torneo) REFERENCES equipo(id_equipo, id_torneo),
    FOREIGN KEY (id_turno) REFERENCES turno(id_turno),
    FOREIGN KEY (nombre_cancha, id_complejo) REFERENCES cancha(nombre_cancha, id_complejo),
    CHECK (id_equipo_local <> id_equipo_visitante)
);

CREATE TABLE planilla_partido (
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(15) NOT NULL,
    id_equipo INT NOT NULL,
    PRIMARY KEY (id_partido, ci_jugador),
    FOREIGN KEY (id_partido) REFERENCES partido(id_partido),
    FOREIGN KEY (id_equipo, ci_jugador) REFERENCES equipo_jugador_torneo(id_equipo, ci_jugador)
);

CREATE TABLE gol (
    id_gol INT AUTO_INCREMENT PRIMARY KEY,
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(15) NOT NULL,
    minuto INT NOT NULL,
    autogol BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK (minuto BETWEEN 0 AND 120),
    FOREIGN KEY (id_partido, ci_jugador) REFERENCES planilla_partido(id_partido, ci_jugador)
);

CREATE TABLE tarjeta (
    id_tarjeta INT AUTO_INCREMENT PRIMARY KEY,
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(15) NOT NULL,
    minuto INT NOT NULL,
    color ENUM('amarilla','roja') NOT NULL,
    CHECK (minuto BETWEEN 0 AND 120),
    FOREIGN KEY (id_partido, ci_jugador) REFERENCES planilla_partido(id_partido, ci_jugador)
);

CREATE TABLE sancion_jugador (
    id_sancion INT AUTO_INCREMENT PRIMARY KEY,
    ci_jugador VARCHAR(15) NOT NULL,
    id_torneo INT NOT NULL,
    motivo ENUM('roja','acumulacion de amarillas','disciplinaria') NOT NULL,
    numero_fecha_inicio INT NOT NULL,
    cantidad_fechas INT NOT NULL DEFAULT 1,
    CHECK (numero_fecha_inicio > 0),
    FOREIGN KEY (ci_jugador) REFERENCES jugador(ci),
    FOREIGN KEY (id_torneo) REFERENCES torneo(id_torneo),
    CHECK (cantidad_fechas >= 1)
);

CREATE USER IF NOT EXISTS 'admin_torneo'@'%' IDENTIFIED BY 'admin1234';
CREATE USER IF NOT EXISTS 'planillero_torneo'@'%' IDENTIFIED BY 'planillero1234';

GRANT ALL PRIVILEGES ON torneo_futbol5.* TO 'admin_torneo'@'%';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'planillero_torneo'@'%';

GRANT SELECT ON torneo_futbol5.facultad TO 'planillero_torneo'@'%';
GRANT SELECT ON torneo_futbol5.jugador TO 'planillero_torneo'@'%';
GRANT SELECT ON torneo_futbol5.torneo TO 'planillero_torneo'@'%';
GRANT SELECT ON torneo_futbol5.equipo TO 'planillero_torneo'@'%';
GRANT SELECT ON torneo_futbol5.equipo_jugador_torneo TO 'planillero_torneo'@'%';
GRANT SELECT ON torneo_futbol5.complejo TO 'planillero_torneo'@'%';
GRANT SELECT ON torneo_futbol5.cancha TO 'planillero_torneo'@'%';
GRANT SELECT ON torneo_futbol5.turno TO 'planillero_torneo'@'%';
GRANT SELECT ON torneo_futbol5.partido TO 'planillero_torneo'@'%';
GRANT SELECT ON torneo_futbol5.sancion_jugador TO 'planillero_torneo'@'%';
GRANT SELECT, INSERT, DELETE ON torneo_futbol5.planilla_partido TO 'planillero_torneo'@'%';
GRANT SELECT, INSERT, DELETE ON torneo_futbol5.gol TO 'planillero_torneo'@'%';
GRANT SELECT, INSERT, DELETE ON torneo_futbol5.tarjeta TO 'planillero_torneo'@'%';
