# Informe del proyecto

## Objetivo

Implementar una base de datos relacional y una API para gestionar un torneo
interfacultades de fútbol 5, incluyendo el registro de equipos y planteles, la
programación de partidos, sus planillas y eventos, las sanciones y los reportes.

## Decisiones de diseño

- Se separaron entidades como facultad, jugador, equipo, torneo, complejo,
  cancha, turno y partido para evitar repetir sus datos en cada operación.
- `equipo_jugador_torneo` representa la pertenencia de un jugador a un equipo en
  una edición concreta. Las claves y restricciones únicas impiden que el mismo
  jugador pertenezca a dos equipos del mismo torneo.
- La planilla relaciona partido, jugador y equipo. Goles y tarjetas dependen de
  esa relación, de modo que un evento no pueda asociarse a un jugador ajeno a la
  planilla del partido.
- Las restricciones `CHECK`, claves foráneas, valores `ENUM` y restricciones
  `UNIQUE` complementan la validación de la API y protegen los datos también
  cuando se accede directamente a MySQL.
- `resultado_partido` calcula los goles de ambos equipos considerando los
  autogoles. Los reportes de posiciones y resultados utilizan esa vista.
- La API autentica con HTTP Basic y distingue los roles administrador y
  planillero. El backend usa credenciales MySQL distintas para cada rol.
- Los reportes operan sobre el torneo solicitado, y la tabla de posiciones parte
  de los equipos para conservar los que aún no jugaron.
- Los reportes solo están disponibles para administradores. El planillero puede
  consultar partidos, equipos y planteles, y registrar planillas, goles y
  tarjetas.

## Mejoras incorporadas al modelo y a las reglas

- Restricciones de integridad para fechas, camisetas, goles, tarjetas y
  pertenencia a torneo/equipo.
- La base impide camisetas repetidas por equipo, fechas de partido y sanción no
  positivas, y la reserva duplicada de una cancha en el mismo día y turno. Un
  índice único condicional permite reutilizar el turno de un partido cancelado.
- La API valida los mismos conflictos de agenda excluyendo partidos cancelados,
  controla planteles, capitanes, sanciones, estados y la ventana de corrección.
- Validaciones de negocio para evitar planteles con más de diez integrantes,
  superar el límite de docentes/funcionarios, mezclar facultades y programar un
  equipo en dos partidos de la misma fecha.
- Control de ocupación de cancha por fecha y turno, y protección de la
  corrección de partidos jugados después de 48 horas.
- Validación de suspensión antes de agregar un jugador a la planilla.
- Registro de sanción posterior a una tarjeta roja o a la acumulación de tres
  amarillas.
- Reporte de fair play con un punto por amarilla y tres por roja, incluyendo
  equipos sin tarjetas.
- Incorporación de equipos sin partidos a la tabla de posiciones, porcentajes
  sin división por cero y tres reportes adicionales: riesgo de suspensión,
  valla menos vencida y jugadores con más tarjetas.
- Los modelos Pydantic validan las entradas de la API, incluidos complejos y
  canchas.

## Bitácora de trabajo

1. Se definió el esquema relacional, sus relaciones y restricciones.
2. Se prepararon datos iniciales, usuarios de base de datos y permisos por rol.
3. Se creó la vista de resultados y se añadieron consultas para los reportes.
4. Se implementó el backend Python, la API y su imagen Docker con validaciones de entrada,
   autenticación y reglas de negocio.
5. Se añadieron tests para el backend, los reportes y los flujos principales de
   la API.
6. Se documentaron la ejecución con Docker Compose, el puerto publicado y la
   ejecución de tests.

## Bibliografía y documentación técnica

- MySQL 8.0 Reference Manual, documentación oficial:
  <https://dev.mysql.com/doc/refman/8.0/en/>
- FastAPI, documentación oficial:
  <https://fastapi.tiangolo.com/>
- Pydantic, documentación oficial:
  <https://docs.pydantic.dev/>
- Docker Compose, documentación oficial:
  <https://docs.docker.com/compose/>
- Consigna del proyecto y material de curso proporcionados para la entrega.
