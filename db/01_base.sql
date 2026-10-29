CREATE DATABASE torneo_futbol5;
USE torneo_futbol5;

CREATE TABLE login (
    correo VARCHAR(100) PRIMARY KEY,
    contrasena VARCHAR(255) NOT NULL,
    rol ENUM('administrador','planillero') NOT NULL
);

CREATE TABLE facultad (
    id_facultad INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE jugador (
    ci VARCHAR(15) PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    apellido VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    fecha_nacimiento DATE NOT NULL,
    id_facultad INT NOT NULL,
    tipo ENUM('grado','posgrado','docente','funcionario') NOT NULL,
    FOREIGN KEY (id_facultad) REFERENCES facultad (id_facultad)
);

CREATE TABLE torneo (
    id_torneo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    anio SMALLINT NOT NULL,
    semestre TINYINT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    estado ENUM('inscripcion','en curso','finalizado') NOT NULL DEFAULT 'inscripcion',
    UNIQUE (anio, semestre)
);

CREATE TABLE equipo (
    id_equipo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    id_torneo INT NOT NULL,
    id_facultad INT NOT NULL,
    ci_capitan VARCHAR(15),
    UNIQUE (id_equipo, id_torneo),
    UNIQUE (id_torneo, nombre),
    FOREIGN KEY (id_torneo) REFERENCES torneo (id_torneo),
    FOREIGN KEY (id_facultad) REFERENCES facultad (id_facultad),
    FOREIGN KEY (ci_capitan) REFERENCES jugador (ci)
);

CREATE TABLE equipo_jugador_torneo (
    id_equipo INT NOT NULL,
    ci_jugador VARCHAR(15) NOT NULL,
    id_torneo INT NOT NULL,
    numero_camiseta TINYINT NOT NULL,
    PRIMARY KEY (id_equipo, ci_jugador, id_torneo),
    UNIQUE (ci_jugador, id_torneo),
    FOREIGN KEY (id_equipo, id_torneo) REFERENCES equipo (id_equipo, id_torneo),
    FOREIGN KEY (ci_jugador) REFERENCES jugador (ci)
);

CREATE TABLE complejo (
    id_complejo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    direccion VARCHAR(150) NOT NULL,
    departamento VARCHAR(50) NOT NULL
);

CREATE TABLE cancha (
    nombre_cancha VARCHAR(50) NOT NULL,
    id_complejo INT NOT NULL,
    superficie ENUM('sintetico','parquet') NOT NULL,
    techada BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (nombre_cancha, id_complejo),
    FOREIGN KEY (id_complejo) REFERENCES complejo (id_complejo)
);

CREATE TABLE turno (
    id_turno INT AUTO_INCREMENT PRIMARY KEY,
    hora_inicio TIME NOT NULL UNIQUE,
    hora_fin TIME NOT NULL
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
    UNIQUE (dia, id_turno, nombre_cancha, id_complejo),
    FOREIGN KEY (id_equipo_local, id_torneo) REFERENCES equipo (id_equipo, id_torneo),
    FOREIGN KEY (id_equipo_visitante, id_torneo) REFERENCES equipo (id_equipo, id_torneo),
    FOREIGN KEY (id_turno) REFERENCES turno (id_turno),
    FOREIGN KEY (nombre_cancha, id_complejo) REFERENCES cancha (nombre_cancha, id_complejo),
    CHECK (id_equipo_local <> id_equipo_visitante)
);

CREATE TABLE planilla_partido (
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(15) NOT NULL,
    id_equipo INT NOT NULL,
    PRIMARY KEY (id_partido, ci_jugador),
    FOREIGN KEY (id_partido) REFERENCES partido (id_partido),
    FOREIGN KEY (ci_jugador) REFERENCES jugador (ci),
    FOREIGN KEY (id_equipo) REFERENCES equipo (id_equipo)
);

CREATE TABLE gol (
    id_gol INT AUTO_INCREMENT PRIMARY KEY,
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(15) NOT NULL,
    minuto TINYINT NOT NULL,
    autogol BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (id_partido, ci_jugador) REFERENCES planilla_partido (id_partido, ci_jugador)
);

CREATE TABLE tarjeta (
    id_tarjeta INT AUTO_INCREMENT PRIMARY KEY,
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(15) NOT NULL,
    minuto TINYINT NOT NULL,
    color ENUM('amarilla','roja') NOT NULL,
    FOREIGN KEY (id_partido, ci_jugador) REFERENCES planilla_partido (id_partido, ci_jugador)
);

CREATE TABLE sancion_jugador (
    id_sancion INT AUTO_INCREMENT PRIMARY KEY,
    ci_jugador VARCHAR(15) NOT NULL,
    id_torneo INT NOT NULL,
    motivo ENUM('roja','acumulacion de amarillas','disciplinaria') NOT NULL,
    numero_fecha_inicio INT NOT NULL,
    cantidad_fechas INT NOT NULL DEFAULT 1,
    FOREIGN KEY (ci_jugador) REFERENCES jugador (ci),
    FOREIGN KEY (id_torneo) REFERENCES torneo (id_torneo)
);


CREATE USER 'admin_torneo'@'%' IDENTIFIED BY 'admin1234';
CREATE USER 'planillero_torneo'@'%' IDENTIFIED BY 'planillero1234';


GRANT ALL PRIVILEGES ON torneo_futbol5.* TO 'admin_torneo'@'%';


GRANT SELECT ON torneo_futbol5.* TO 'planillero_torneo'@'%';
GRANT INSERT, UPDATE, DELETE ON torneo_futbol5.planilla_partido TO 'planillero_torneo'@'%';
GRANT INSERT, UPDATE, DELETE ON torneo_futbol5.gol TO 'planillero_torneo'@'%';
GRANT INSERT, UPDATE, DELETE ON torneo_futbol5.tarjeta TO 'planillero_torneo'@'%';