import pytest

import backend


class FakeCursor:
    def __init__(self, error=None):
        self.error = error
        self.lastrowid = 7
        self.rowcount = 1
        self.closed = False

    def execute(self, sql, params):
        if self.error:
            raise self.error

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_instance = cursor
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self, **kwargs):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def test_execute_confirma_y_cierra_la_conexion(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    monkeypatch.setattr(backend, "connect_db", lambda: connection)

    result = backend.execute("INSERT INTO jugador (ci) VALUES (%s)", ("1",))

    assert result == (7, 1)
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closed
    assert cursor.closed


def test_execute_hace_rollback_y_propaga_el_error(monkeypatch):
    cursor = FakeCursor(RuntimeError("error de prueba"))
    connection = FakeConnection(cursor)
    monkeypatch.setattr(backend, "connect_db", lambda: connection)

    with pytest.raises(RuntimeError, match="error de prueba"):
        backend.execute("UPDATE jugador SET nombre=%s", ("Ana",))

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closed
    assert cursor.closed
