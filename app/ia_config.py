import os
import re
from pathlib import Path


def _env_path():
    return Path(__file__).resolve().parents[1] / ".env"


def cargar_valor_env(nombre):
    valor = os.getenv(nombre)
    if valor:
        return valor

    env_path = _env_path()
    if not env_path.exists():
        return None

    with open(env_path, "r", encoding="utf-8-sig") as env_file:
        for linea in env_file:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            if clave.strip() == nombre:
                return valor.strip().strip('"').strip("'") or None

    return None


def cargar_lista_apis():
    claves = []
    valor_entorno = os.getenv("LISTA_APIS")
    if valor_entorno:
        claves.extend(re.findall(r"gsk_[A-Za-z0-9]+", valor_entorno))

    env_path = _env_path()
    if not env_path.exists():
        return claves

    recolectando = False
    bloque = []
    with open(env_path, "r", encoding="utf-8-sig") as env_file:
        for linea in env_file:
            texto = linea.strip()
            if not texto or texto.startswith("#"):
                continue

            if recolectando:
                bloque.append(texto)
                if "]" in texto:
                    break
                continue

            if "=" not in texto:
                continue

            clave, valor = texto.split("=", 1)
            if clave.strip() == "LISTA_APIS":
                bloque.append(valor.strip())
                if "]" not in valor:
                    recolectando = True

    if bloque:
        claves.extend(re.findall(r"gsk_[A-Za-z0-9]+", "\n".join(bloque)))

    unicas = []
    for clave in claves:
        if clave and clave not in unicas:
            unicas.append(clave)
    return unicas


def cargar_configuraciones_ia():
    proveedor = (cargar_valor_env("AI_PROVIDER") or "").strip().lower()
    groq_api_key = cargar_valor_env("GROQ_API_KEY")
    openai_api_key = cargar_valor_env("OPENAI_API_KEY")
    groq_model = cargar_valor_env("GROQ_MODEL") or "openai/gpt-oss-20b"
    openai_model = cargar_valor_env("OPENAI_MODEL") or "gpt-4.1-mini"

    configuraciones = []

    def agregar_openai():
        if openai_api_key:
            configuraciones.append({
                "proveedor": "openai",
                "api_key": openai_api_key,
                "base_url": None,
                "model": openai_model,
            })

    def agregar_groq():
        claves_groq = []
        if groq_api_key:
            claves_groq.append(groq_api_key)
        claves_groq.extend(cargar_lista_apis())

        for indice, clave in enumerate(dict.fromkeys(claves_groq), start=1):
            configuraciones.append({
                "proveedor": "groq",
                "api_key": clave,
                "base_url": "https://api.groq.com/openai/v1",
                "model": groq_model,
                "alias": f"GROQ #{indice}",
            })

    if proveedor == "openai":
        agregar_openai()
        agregar_groq()
    else:
        agregar_groq()
        agregar_openai()

    return configuraciones


def cargar_configuracion_ia():
    configuraciones = cargar_configuraciones_ia()
    if configuraciones:
        return configuraciones[0]

    proveedor = (cargar_valor_env("AI_PROVIDER") or "groq").strip().lower()
    return {
        "proveedor": proveedor,
        "api_key": None,
        "base_url": "https://api.groq.com/openai/v1" if proveedor == "groq" else None,
        "model": cargar_valor_env("GROQ_MODEL") or cargar_valor_env("OPENAI_MODEL") or "openai/gpt-oss-20b",
    }


def ocultar_claves(texto):
    limpio = str(texto)
    for config in cargar_configuraciones_ia():
        clave = config.get("api_key")
        if clave:
            limpio = limpio.replace(clave, "[API_KEY]")
    return limpio


def detalle_error_ia(error, config):
    mensaje_error = ocultar_claves(error)
    proveedor = (config.get("alias") or config.get("proveedor") or "IA").upper()
    if "401" in mensaje_error or "invalid_api_key" in mensaje_error:
        return f"La clave de {proveedor} fue rechazada."
    if "429" in mensaje_error or "insufficient_quota" in mensaje_error:
        return f"{proveedor} rechazo la solicitud por cuota insuficiente."
    if "413" in mensaje_error or "Request too large" in mensaje_error or "rate_limit_exceeded" in mensaje_error:
        return f"{proveedor} rechazo la solicitud por limite de tokens."
    if "model_not_found" in mensaje_error or "does not exist" in mensaje_error:
        return f"El modelo configurado para {proveedor} no esta disponible."
    return f"No se pudo recomendar con {proveedor}: {mensaje_error[:500]}"
