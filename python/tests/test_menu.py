import json
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

import menu


def test_api_client_sends_basic_auth_and_json():
    response = BytesIO(b'{"mensaje":"ok"}')
    response.status = 200
    with patch("menu.urlopen", return_value=response) as urlopen:
        client = menu.APIClient("http://localhost:8000/", "user", "pass")
        result = client.post("/partidos/1/goles", {"minuto": 8})

    request = urlopen.call_args.args[0]
    assert request.get_header("Authorization") == "Basic dXNlcjpwYXNz"
    assert json.loads(request.data) == {"minuto": 8}
    assert result == {"mensaje": "ok"}


def test_api_client_reports_http_error():
    response = BytesIO(b'{"detail":"Forbidden"}')
    error = HTTPError("http://localhost:8000/reportes", 403, "Forbidden", {}, response)
    with patch("menu.urlopen", side_effect=error):
        client = menu.APIClient("http://localhost:8000", "user", "pass")

        try:
            client.get("/reportes")
        except menu.APIError as caught:
            assert str(caught) == "HTTP 403: Forbidden"
        else:
            raise AssertionError("Expected APIError")


def test_api_client_supports_update_and_delete():
    def fake_urlopen(_request, timeout):
        response = BytesIO(b'{"mensaje":"ok"}')
        response.status = 200
        return response

    with patch("menu.urlopen", side_effect=fake_urlopen) as urlopen:
        client = menu.APIClient("http://localhost:8000", "user", "pass")
        client.put("/equipos/1", {"nombre": "Equipo"})
        client.delete("/equipos/1")

    assert urlopen.call_args_list[0].args[0].get_method() == "PUT"
    assert urlopen.call_args_list[1].args[0].get_method() == "DELETE"


def test_planillero_menu_hides_admin_options():
    cliente = type("FakeClient", (), {"get": lambda self, path: []})()
    respuestas = iter(["0"])
    salida = []

    menu.ejecutar_menu(cliente, "planillero", entrada=lambda _: next(respuestas), salida=salida.append)

    texto = "\n".join(salida)
    assert "Registrar planilla, gol o tarjeta" in texto
    assert "ABM de jugadores" not in texto
    assert "Resultados y reportes" not in texto


def test_main_usa_el_rol_autenticado_y_no_pide_elegirlo():
    respuestas = iter(["http://localhost:8000", "planillero@ucu.edu.uy", "0"])
    salida = []
    cliente = type(
        "FakeClient",
        (),
        {"get": lambda self, path: {"rol": "planillero"}},
    )()

    with patch("menu.APIClient", return_value=cliente):
        menu.main(
            entrada=lambda _: next(respuestas),
            salida=salida.append,
            pedir_contrasena=lambda _: "planillero123",
        )

    texto = "\n".join(salida)
    assert "Sesión iniciada como planillero" in texto
    assert "ABM de jugadores" not in texto


def test_pedir_campo_repite_hasta_validar_datos():
    respuestas = iter(["correo-invalido", "persona@example.com"])
    assert menu.pedir_campo("Correo", "email", entrada=lambda _: next(respuestas)) == "persona@example.com"
