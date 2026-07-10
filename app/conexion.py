from urllib.parse import urlparse, unquote

import pymysql

try:
    from .config import cargar_primero, cargar_valor_env
except ImportError:
    from config import cargar_primero, cargar_valor_env


def _config_desde_database_url(database_url):
    if not database_url:
        return {}

    url = urlparse(database_url)
    if url.scheme not in ("mysql", "mysql+pymysql"):
        return {}

    return {
        "host": url.hostname,
        "port": url.port or 3306,
        "user": unquote(url.username or ""),
        "password": unquote(url.password or ""),
        "database": (url.path or "").lstrip("/"),
    }


def _config_mysql():
    config_url = _config_desde_database_url(cargar_valor_env("DATABASE_URL"))
    return {
        "host": config_url.get("host") or cargar_primero("DB_HOST", "MYSQL_HOST", defecto="127.0.0.1"),
        "port": int(config_url.get("port") or cargar_primero("DB_PORT", "MYSQL_PORT", defecto="3306")),
        "user": config_url.get("user") or cargar_primero("DB_USER", "MYSQL_USER", defecto="root"),
        "password": config_url.get("password") or cargar_primero("DB_PASSWORD", "MYSQL_PASSWORD", defecto=""),
        "database": config_url.get("database") or cargar_primero("DB_NAME", "MYSQL_DATABASE", "DATABASE_NAME", defecto="gestion_riesgo"),
        "ssl_mode": cargar_primero("DB_SSL_MODE", "MYSQL_SSL_MODE", defecto="REQUIRED"),
    }

def conectar():
    try:
        config = _config_mysql()
        ssl_mode = (config.pop("ssl_mode") or "").strip()
        ssl_config = {"ssl_mode": ssl_mode} if ssl_mode and ssl_mode.upper() != "DISABLED" else None
        conn = pymysql.connect(
            **config,
            cursorclass=pymysql.cursors.DictCursor,
            ssl=ssl_config,
        )
        return conn
    except Exception as error:
        print(f"No se pudo conectar a MySQL: {error}")
        return ''
