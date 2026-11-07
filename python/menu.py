
import base64
import getpass
import json
import re
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


REPORTES = {
    "1": ("Tabla de posiciones", "/reportes/tabla-posiciones"),
    "2": ("Goleadores", "/reportes/goleadores"),
    "3": ("Fair play", "/reportes/fair-play"),
    "4": ("Promedio de goles por fecha", "/reportes/promedio-goles"),
    "5": ("Porcentaje de partidos jugados", "/reportes/porcentaje-jugados"),
    "6": ("Canchas y turnos", "/reportes/canchas-turnos"),
    "7": ("Jugadores por facultad y tipo", "/reportes/jugadores-facultad-tipo"),
    "8": ("Jugadores sin planilla", "/reportes/jugadores-sin-planilla"),
    "9": ("Sanciones por equipo y motivo", "/reportes/sanciones-equipo-motivo"),
    "10": ("Jugadores con más tarjetas", "/reportes/jugadores-tarjetas"),
    "11": ("Riesgo de suspensión", "/reportes/riesgo-suspension"),
    "12": ("Valla menos vencida", "/reportes/valla-menos-vencida"),
}

TIPOS_JUGADOR = ("grado", "posgrado", "docente", "funcionario")
ESTADOS_PARTIDO = ("programado", "jugado", "postergado", "cancelado")
ESTADOS_TORNEO = ("inscripcion", "en curso", "finalizado")
MOTIVOS_SANCION = ("roja", "acumulacion de amarillas", "disciplinaria")


class APIError(Exception):
    pass


class APIClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        self.authorization = f"Basic {token}"

    def request(self, method, path, payload=None):
        data = None
        headers = {"Authorization": self.authorization, "Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=10) as response:
                body = response.read()
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(detail)
                detail = parsed.get("detail", parsed.get("error", detail))
            except json.JSONDecodeError:
                pass
            raise APIError(f"HTTP {error.code}: {detail}") from error
        except URLError as error:
            raise APIError(f"No se pudo conectar con la API: {error.reason}") from error

        if not body:
            return None
        return json.loads(body.decode("utf-8"))

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, payload):
        return self.request("POST", path, payload)

    def put(self, path, payload):
        return self.request("PUT", path, payload)

    def delete(self, path):
        return self.request("DELETE", path)


def mostrar(datos, salida=print):
    if isinstance(datos, list):
        if not datos:
            salida("Sin resultados.")
            return
        if all(isinstance(fila, dict) for fila in datos):
            columnas = list(dict.fromkeys(clave for fila in datos for clave in fila))
            filas = [[fila.get(columna) for columna in columnas] for fila in datos]
            _mostrar_tabla(columnas, filas, salida)
            return
    elif isinstance(datos, dict):
        _mostrar_tabla(("Campo", "Valor"), list(datos.items()), salida)
        return
    salida(json.dumps(datos, ensure_ascii=False, indent=2))


def _mostrar_tabla(columnas, filas, salida):
    encabezados = [str(columna).replace("_", " ").title() for columna in columnas]
    celdas = [[_formatear_valor(valor) for valor in fila] for fila in filas]
    anchos = [
        max(len(encabezado), *(len(fila[indice]) for fila in celdas))
        for indice, encabezado in enumerate(encabezados)
    ]

    def linea(fila):
        return " | ".join(valor.ljust(anchos[indice]) for indice, valor in enumerate(fila))

    salida(linea(encabezados))
    salida("+".join("-" * ancho for ancho in anchos))
    for fila in celdas:
        salida(linea(fila))


def _formatear_valor(valor):
    if valor is None:
        return "-"
    if isinstance(valor, (dict, list)):
        texto = json.dumps(valor, ensure_ascii=False, separators=(",", ": "))
    else:
        texto = str(valor)
    return texto.replace("\r", " ").replace("\n", " ")


def _formato_numero(minimo, maximo):
    if maximo is not None:
        return f"número entero entre {minimo} y {maximo}"
    if minimo == 1:
        return "número entero positivo"
    return f"número entero mayor o igual a {minimo}"


def pedir_entero(mensaje, entrada=input, minimo=1, maximo=None):
    etiqueta = mensaje.rstrip().removesuffix(":")
    prompt = f"{etiqueta} ({_formato_numero(minimo, maximo)}): "
    while True:
        valor = entrada(prompt).strip()
        try:
            numero = int(valor)
            if numero >= minimo and (maximo is None or numero <= maximo):
                return numero
        except ValueError:
            pass
        limite = f" y menor o igual a {maximo}" if maximo is not None else ""
        print(f"Ingresá un número entero mayor o igual a {minimo}{limite}.")


def pedir_campo(nombre, tipo, entrada=input, opciones=(), minimo=1, maximo=None, opcional=False):
    formatos = {
        "texto": f"texto obligatorio, máximo {maximo} caracteres"
        if maximo is not None
        else "texto obligatorio",
        "ci": "solo números, entre 6 y 8 dígitos",
        "email": "correo válido (ej.: nombre@dominio.com)",
        "fecha": "formato AAAA-MM-DD (ej.: 2026-11-24)",
        "numero": _formato_numero(minimo, maximo),
        "opcion": f"opciones: {', '.join(opciones)}",
        "booleano": "respondé s o n",
    }
    formato = formatos.get(tipo)
    if opcional:
        formato = f"{formato}; opcional"
    prompt = f"{nombre} ({formato}): " if formato else f"{nombre}: "
    while True:
        valor = entrada(prompt).strip()
        if opcional and not valor:
            return None
        if tipo == "texto":
            if valor and (maximo is None or len(valor) <= maximo):
                return valor
        elif tipo == "ci":
            if re.fullmatch(r"\d{6,8}", valor):
                return valor
        elif tipo == "email":
            if len(valor) <= 100 and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", valor):
                return valor
        elif tipo == "fecha":
            try:
                date.fromisoformat(valor)
                return valor
            except ValueError:
                pass
        elif tipo == "numero":
            try:
                numero = int(valor)
                if numero >= minimo and (maximo is None or numero <= maximo):
                    return numero
            except ValueError:
                pass
        elif tipo == "opcion" and valor in opciones:
            return valor
        elif tipo == "booleano" and valor.lower() in ("s", "si", "n", "no"):
            return valor.lower() in ("s", "si")
        if tipo == "opcion":
            print(f"Elegí uno de estos valores: {', '.join(opciones)}.")
        elif tipo == "ci":
            print("La CI debe tener entre 6 y 8 dígitos.")
        elif tipo == "email":
            print("Ingresá un correo válido.")
        elif tipo == "fecha":
            print("Ingresá una fecha válida con formato AAAA-MM-DD.")
        elif tipo == "texto":
            print("El texto no puede estar vacío ni superar el largo permitido.")
        elif tipo == "booleano":
            print("Respondé s o n.")
        else:
            limite = f" y no superar {maximo}" if maximo is not None else ""
            print(f"Ingresá un número entero entre {minimo}{limite}.")


def capturar_campos(campos, entrada=input):
    payload = {}
    for nombre, tipo, opciones, minimo, maximo, opcional in campos:
        payload[nombre] = pedir_campo(
            nombre.replace("_", " "),
            tipo,
            entrada,
            opciones=opciones,
            minimo=minimo,
            maximo=maximo,
            opcional=opcional,
        )
    return payload


def pedir_identificador(nombre, entrada=input):
    if nombre.lower() == "ci":
        return pedir_campo("CI", "ci", entrada)
    if "nombre" in nombre.lower():
        return pedir_campo(nombre, "texto", entrada, maximo=50)
    return str(pedir_entero(f"{nombre}: ", entrada))


def menu_abm(
    cliente,
    nombre,
    ruta,
    campos,
    id_nombre,
    entrada=input,
    salida=print,
    campos_modificar=None,
):
    if campos_modificar is None:
        campos_modificar = campos
    while True:
        salida(f"\n--- {nombre} ---")
        salida("1. Listar")
        salida("2. Crear")
        salida("3. Modificar")
        salida("4. Eliminar")
        salida("0. Volver")
        opcion = entrada("Opción: ").strip()
        try:
            if opcion == "0":
                return
            if opcion == "1":
                mostrar(cliente.get(ruta), salida)
            elif opcion == "2":
                mostrar(cliente.post(ruta, capturar_campos(campos, entrada)), salida)
            elif opcion == "3":
                id_objeto = pedir_identificador(id_nombre, entrada)
                payload = capturar_campos(campos_modificar, entrada)
                if "ci" in payload:
                    payload["ci"] = id_objeto
                mostrar(
                    cliente.put(f"{ruta}/{quote(id_objeto, safe='')}", payload),
                    salida,
                )
            elif opcion == "4":
                id_objeto = pedir_identificador(id_nombre, entrada)
                if entrada("¿Confirmás la eliminación? (s/n): ").strip().lower() == "s":
                    mostrar(cliente.delete(f"{ruta}/{quote(id_objeto, safe='')}"), salida)
            else:
                salida("Opción inválida.")
        except APIError as error:
            salida(f"Error: {error}")


CAMPOS_JUGADOR = (
    ("ci", "ci", (), 1, None, False),
    ("nombre", "texto", (), 1, 50, False),
    ("apellido", "texto", (), 1, 50, False),
    ("email", "email", (), 1, None, False),
    ("fecha_nacimiento", "fecha", (), 1, None, False),
    ("id_facultad", "numero", (), 1, None, False),
    ("tipo", "opcion", TIPOS_JUGADOR, 1, None, False),
)
CAMPOS_EQUIPO_CREAR = (
    ("nombre", "texto", (), 1, 100, False),
    ("id_torneo", "numero", (), 1, None, False),
    ("id_facultad", "numero", (), 1, None, False),
)
CAMPOS_EQUIPO_MODIFICAR = CAMPOS_EQUIPO_CREAR + (
    ("ci_capitan", "ci", (), 1, None, True),
)
CAMPOS_COMPLEJO = (
    ("nombre", "texto", (), 1, 100, False),
    ("direccion", "texto", (), 1, 150, False),
    ("departamento", "texto", (), 1, 50, False),
)
CAMPOS_PARTIDO = (
    ("id_torneo", "numero", (), 1, None, False),
    ("numero_fecha", "numero", (), 1, None, False),
    ("id_equipo_local", "numero", (), 1, None, False),
    ("id_equipo_visitante", "numero", (), 1, None, False),
    ("dia", "fecha", (), 1, None, False),
    ("id_turno", "numero", (), 1, None, False),
    ("nombre_cancha", "texto", (), 1, 50, False),
    ("id_complejo", "numero", (), 1, None, False),
    ("estado", "opcion", ESTADOS_PARTIDO, 1, None, False),
)
CAMPOS_SANCION = (
    ("ci_jugador", "ci", (), 1, None, False),
    ("id_torneo", "numero", (), 1, None, False),
    ("motivo", "opcion", MOTIVOS_SANCION, 1, None, False),
    ("numero_fecha_inicio", "numero", (), 1, None, False),
    ("cantidad_fechas", "numero", (), 1, None, False),
)


def administrar_planteles(cliente, entrada=input, salida=print):
    while True:
        salida("\n--- Planteles y capitanes ---")
        salida("1. Ver plantel")
        salida("2. Agregar jugador al plantel")
        salida("3. Quitar jugador del plantel")
        salida("4. Cambiar capitán")
        salida("0. Volver")
        opcion = entrada("Opción: ").strip()
        try:
            if opcion == "0":
                return
            equipo_id = pedir_entero("ID del equipo: ", entrada)
            if opcion == "1":
                mostrar(cliente.get(f"/equipos/{equipo_id}/jugadores"), salida)
            elif opcion == "2":
                jugador = pedir_campo("CI del jugador", "ci", entrada)
                camiseta = pedir_entero("Número de camiseta", entrada, 1, 99)
                mostrar(
                    cliente.post(
                        f"/equipos/{equipo_id}/jugadores",
                        {"ci_jugador": jugador, "numero_camiseta": camiseta},
                    ),
                    salida,
                )
            elif opcion == "3":
                ci = pedir_campo("CI del jugador", "ci", entrada)
                if entrada("¿Confirmás quitarlo? (s/n): ").strip().lower() == "s":
                    mostrar(cliente.delete(f"/equipos/{equipo_id}/jugadores/{ci}"), salida)
            elif opcion == "4":
                ci = pedir_campo("CI del nuevo capitán", "ci", entrada)
                mostrar(
                    cliente.put(f"/equipos/{equipo_id}/capitan", {"ci_jugador": ci}),
                    salida,
                )
            else:
                salida("Opción inválida.")
        except APIError as error:
            salida(f"Error: {error}")


def administrar_canchas(cliente, entrada=input, salida=print):
    complejo_id = pedir_entero("ID del complejo: ", entrada)
    ruta = f"/complejos/{complejo_id}/canchas"
    campos = (
        ("nombre_cancha", "texto", (), 1, 50, False),
        ("superficie", "opcion", ("sintetico", "parquet"), 1, None, False),
        ("techada", "booleano", (), 1, None, False),
    )
    campos_modificar = (
        ("superficie", "opcion", ("sintetico", "parquet"), 1, None, False),
        ("techada", "booleano", (), 1, None, False),
    )
    menu_abm(
        cliente,
        "Canchas",
        ruta,
        campos,
        "nombre de la cancha",
        entrada,
        salida,
        campos_modificar,
    )


def administrar_torneos(cliente, entrada=input, salida=print):
    campos = (
        ("nombre", "texto", (), 1, 100, False),
        ("anio", "numero", (), 2000, 2100, False),
        ("semestre", "numero", (), 1, 2, False),
        ("fecha_inicio", "fecha", (), 1, None, False),
        ("fecha_fin", "fecha", (), 1, None, False),
    )
    while True:
        salida("\n--- Torneos ---")
        salida("1. Listar")
        salida("2. Crear")
        salida("3. Avanzar estado")
        salida("0. Volver")
        opcion = entrada("Opción: ").strip()
        try:
            if opcion == "0":
                return
            if opcion == "1":
                mostrar(cliente.get("/torneos"), salida)
            elif opcion == "2":
                mostrar(cliente.post("/torneos", capturar_campos(campos, entrada)), salida)
            elif opcion == "3":
                torneo_id = pedir_entero("ID del torneo: ", entrada)
                estado = pedir_campo("Nuevo estado", "opcion", entrada, opciones=ESTADOS_TORNEO)
                mostrar(cliente.put(f"/torneos/{torneo_id}/estado", {"estado": estado}), salida)
            else:
                salida("Opción inválida.")
        except APIError as error:
            salida(f"Error: {error}")


def administrar_resultados(cliente, entrada=input, salida=print):
    while True:
        salida("\n--- Resultados y reportes ---")
        salida("1. Ver resultado de un partido")
        salida("2. Consultar reportes")
        salida("0. Volver")
        opcion = entrada("Opción: ").strip()
        try:
            if opcion == "0":
                return
            if opcion == "1":
                partido_id = pedir_entero("ID del partido: ", entrada)
                mostrar(cliente.get(f"/partidos/{partido_id}/resultado"), salida)
            elif opcion == "2":
                for numero, (nombre, _) in REPORTES.items():
                    salida(f"{numero}. {nombre}")
                reporte = entrada("Reporte: ").strip()
                if reporte not in REPORTES:
                    salida("Opción de reporte inválida.")
                    continue
                torneo_id = pedir_entero("ID del torneo: ", entrada)
                ruta = f"{REPORTES[reporte][1]}?torneo_id={torneo_id}"
                mostrar(cliente.get(ruta), salida)
            else:
                salida("Opción inválida.")
        except APIError as error:
            salida(f"Error: {error}")


def registrar_eventos(cliente, entrada=input, salida=print):
    while True:
        salida("\n--- Planilla del partido ---")
        salida("1. Agregar jugador")
        salida("2. Registrar gol")
        salida("3. Registrar tarjeta")
        salida("0. Volver")
        opcion = entrada("Opción: ").strip()
        if opcion == "0":
            return
        try:
            partido_id = pedir_entero("ID del partido: ", entrada)
            ci = pedir_campo("CI del jugador", "ci", entrada)
            if opcion == "1":
                equipo_id = pedir_entero("ID del equipo: ", entrada)
                ruta = f"/partidos/{partido_id}/planilla"
                payload = {"ci_jugador": ci, "id_equipo": equipo_id}
            elif opcion == "2":
                minuto = pedir_entero("Minuto", entrada, 0, 120)
                autogol = pedir_campo("¿Fue autogol? (s/n)", "booleano", entrada)
                ruta = f"/partidos/{partido_id}/goles"
                payload = {"ci_jugador": ci, "minuto": minuto, "autogol": autogol}
            elif opcion == "3":
                minuto = pedir_entero("Minuto", entrada, 0, 120)
                color = pedir_campo(
                    "Tarjeta", "opcion", entrada, opciones=("amarilla", "roja")
                )
                ruta = f"/partidos/{partido_id}/tarjetas"
                payload = {"ci_jugador": ci, "minuto": minuto, "color": color}
            else:
                salida("Opción inválida.")
                continue
            mostrar(cliente.post(ruta, payload), salida)
        except APIError as error:
            salida(f"Error: {error}")


def ver_eventos(cliente, entrada=input, salida=print):
    partido_id = pedir_entero("ID del partido: ", entrada)
    for nombre, recurso in (("Planilla", "planilla"), ("Goles", "goles"), ("Tarjetas", "tarjetas")):
        salida(f"\n{nombre}:")
        mostrar(cliente.get(f"/partidos/{partido_id}/{recurso}"), salida)


def ejecutar_menu(cliente, rol, entrada=input, salida=print):
    while True:
        salida("\n=== TORNEO INTERFACULTADES ===")
        salida("1. Ver partidos")
        salida("2. Ver equipos")
        salida("3. Ver plantel de un equipo")
        salida("4. Registrar planilla, gol o tarjeta")
        if rol == "administrador":
            salida("5. ABM de jugadores")
            salida("6. ABM de equipos")
            salida("7. ABM de planteles y capitanes")
            salida("8. ABM de complejos")
            salida("9. ABM de canchas")
            salida("10. ABM de partidos")
            salida("11. ABM de sanciones")
            salida("12. Gestionar torneos")
            salida("13. Resultados y reportes")
            salida("14. Ver planilla, goles y tarjetas")
        salida("0. Salir")
        opcion = entrada("Opción: ").strip()

        try:
            if opcion == "0":
                salida("Hasta luego.")
                return
            if opcion == "1":
                mostrar(cliente.get("/partidos"), salida)
            elif opcion == "2":
                mostrar(cliente.get("/equipos"), salida)
            elif opcion == "3":
                equipo_id = pedir_entero("ID del equipo: ", entrada)
                mostrar(cliente.get(f"/equipos/{equipo_id}/jugadores"), salida)
            elif opcion == "4":
                registrar_eventos(cliente, entrada, salida)
            elif rol == "administrador" and opcion == "5":
                menu_abm(cliente, "Jugadores", "/jugadores", CAMPOS_JUGADOR, "CI", entrada, salida)
            elif rol == "administrador" and opcion == "6":
                menu_abm(
                    cliente,
                    "Equipos",
                    "/equipos",
                    CAMPOS_EQUIPO_CREAR,
                    "ID del equipo",
                    entrada,
                    salida,
                    campos_modificar=CAMPOS_EQUIPO_MODIFICAR,
                )
            elif rol == "administrador" and opcion == "7":
                administrar_planteles(cliente, entrada, salida)
            elif rol == "administrador" and opcion == "8":
                menu_abm(
                    cliente,
                    "Complejos",
                    "/complejos",
                    CAMPOS_COMPLEJO,
                    "ID del complejo",
                    entrada,
                    salida,
                )
            elif rol == "administrador" and opcion == "9":
                administrar_canchas(cliente, entrada, salida)
            elif rol == "administrador" and opcion == "10":
                menu_abm(
                    cliente,
                    "Partidos",
                    "/partidos",
                    CAMPOS_PARTIDO,
                    "ID del partido",
                    entrada,
                    salida,
                )
            elif rol == "administrador" and opcion == "11":
                menu_abm(
                    cliente,
                    "Sanciones",
                    "/sanciones",
                    CAMPOS_SANCION,
                    "ID de la sanción",
                    entrada,
                    salida,
                )
            elif rol == "administrador" and opcion == "12":
                administrar_torneos(cliente, entrada, salida)
            elif rol == "administrador" and opcion == "13":
                administrar_resultados(cliente, entrada, salida)
            elif rol == "administrador" and opcion == "14":
                ver_eventos(cliente, entrada, salida)
            else:
                salida("Opción inválida.")
        except APIError as error:
            salida(f"Error: {error}")


def main(entrada=input, salida=print, pedir_contrasena=getpass.getpass):
    username = entrada("Correo: ").strip()
    password = pedir_contrasena("Contraseña: ")
    cliente = APIClient("http://localhost:8000", username, password)

    try:
        sesion = cliente.get("/sesion")
    except APIError as error:
        salida(f"No se pudo iniciar sesión: {error}")
        return

    rol = sesion["rol"]
    salida(f"Sesión iniciada como {rol}.")
    ejecutar_menu(cliente, rol, entrada, salida)


if __name__ == "__main__":
    main()
