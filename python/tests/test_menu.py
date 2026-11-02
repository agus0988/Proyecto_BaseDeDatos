import menu


def test_pedir_torneo_usa_uno_por_defecto(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")

    assert menu.pedir_torneo() == 1


def test_pedir_torneo_rechaza_valores_invalidos(monkeypatch, capsys):
    respuestas = iter(["abc", "0", "-1", "3"])
    monkeypatch.setattr("builtins.input", lambda _: next(respuestas))

    assert menu.pedir_torneo() == 3
    assert capsys.readouterr().out.count("El ID debe") == 3


def test_ejecutar_menu_sale_con_cero(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "0")

    menu.ejecutar_menu()

    salida = capsys.readouterr().out
    assert "0. Salir" in salida
    assert "Hasta luego." in salida
