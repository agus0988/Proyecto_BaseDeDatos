
import os

import mysql.connector


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3307")),
    "database": os.getenv("DB_NAME", "torneo_futbol5"),
}

DB_USERS = {
    "administrador": (
        os.getenv("DB_USER", "admin_torneo"),
        os.getenv("DB_PASSWORD", "admin1234"),
    ),
    "planillero": (
        os.getenv("DB_PLANILLERO_USER", "planillero_torneo"),
        os.getenv("DB_PLANILLERO_PASSWORD", "planillero1234"),
    ),
}


def connect_db(rol="administrador"):
    usuario, clave = DB_USERS[rol]
    return mysql.connector.connect(**{**DB_CONFIG, "user": usuario, "password": clave})


def fetch_all(sql, params=(), rol="administrador"):
    connection = connect_db(rol)
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def fetch_one(sql, params=(), rol="administrador"):
    connection = connect_db(rol)
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


def execute(sql, params=(), rol="administrador"):
    connection = connect_db(rol)
    cursor = connection.cursor()
    try:
        cursor.execute(sql, params)
        connection.commit()
        return cursor.lastrowid, cursor.rowcount
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    print(fetch_one("SELECT 1 AS conexion"))
