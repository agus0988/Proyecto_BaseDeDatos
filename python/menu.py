"""Menú de consola para ejecutar los reportes del torneo."""

from pprint import pprint

import mysql.connector

from consultas import (
    canchas_y_turnos_mas_utilizados,
    fair_play_por_equipo,
    goles_por_fecha,
    jugadores_con_mas_tarjetas,
    jugadores_por_equipo,
    jugadores_por_facultad_y_tipo,
    jugadores_que_nunca_estuvieron_en_planilla,
    partidos_disputados_por_fecha,
    partidos_jugados_por_equipo,
    partidos_por_estado,
    sanciones_por_equipo_y_motivo,
    tabla_goleadores,
)


OPCIONES = {
    "1": ("Partidos jugados por equipo", partidos_jugados_por_equipo),
    "2": ("Tabla de goleadores", tabla_goleadores),
    "3": ("Fair play por equipo", fair_play_por_equipo),
    "4": ("Goles por fecha", goles_por_fecha),
    "5": ("Canchas y turnos más utilizados", canchas_y_turnos_mas_utilizados),
    "6": ("Jugadores por facultad y tipo", jugadores_por_facultad_y_tipo),
    "7": (
        "Jugadores que nunca estuvieron en una planilla",
        jugadores_que_nunca_estuvieron_en_planilla,
    ),
    "8": ("Sanciones por equipo y motivo", sanciones_por_equipo_y_motivo),
    "9": ("Partidos por estado", partidos_por_estado),
    "10": ("Jugadores con más tarjetas", jugadores_con_mas_tarjetas),
    "11": ("Partidos disputados por fecha", partidos_disputados_por_fecha),
    "12": ("Cantidad de jugadores por equipo", jugadores_por_equipo),
}


def mostrar_menu():
    print("\n=== REPORTES DEL TORNEO ===")
    for numero, (nombre, _) in OPCIONES.items():
        print(f"{numero}. {nombre}")
    print("0. Salir")


def pedir_torneo():
    while True:
        valor = input("Ingrese el ID del torneo [1]: ").strip()
        if not valor:
            return 1
        if valor.isdigit() and int(valor) > 0:
            return int(valor)
        print("El ID debe ser un número entero positivo.")


def ejecutar_menu():
    while True:
        mostrar_menu()
        opcion = input("Seleccione una opción: ").strip()

        if opcion == "0":
            print("Hasta luego.")
            break

        if opcion not in OPCIONES:
            print("Opción inválida.")
            continue

        nombre, consulta = OPCIONES[opcion]
        torneo_id = pedir_torneo()
        print(f"\n--- {nombre} ---")
        try:
            pprint(consulta(torneo_id))
        except mysql.connector.Error as error:
            print(f"No se pudo ejecutar la consulta: {error}")


if __name__ == "__main__":
    ejecutar_menu()
