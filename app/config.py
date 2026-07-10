import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def cargar_valor_env(nombre, defecto=None):
    valor = os.getenv(nombre)
    if valor not in (None, ""):
        return valor.strip()

    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return defecto

    with open(env_path, "r", encoding="utf-8-sig") as env_file:
        for linea in env_file:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue

            clave, valor = linea.split("=", 1)
            if clave.strip() == nombre:
                valor = valor.strip().strip('"').strip("'")
                return valor if valor else defecto

    return defecto


def cargar_primero(*nombres, defecto=None):
    for nombre in nombres:
        valor = cargar_valor_env(nombre)
        if valor not in (None, ""):
            return valor
    return defecto
