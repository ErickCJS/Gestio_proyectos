from pathlib import Path
import html
import io
import re
import zipfile

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse, Response



try:
    from .routes import usuario, procesos, riesgos, controles
    from . import conexion
except ImportError:
    from routes import usuario, procesos, riesgos, controles
    import conexion

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
def usuario_actual(request):
    return request.session.get("usuario") or {
        "nombre": "Administrador",
        "correo": "administrador@magerisk.local"
    }

templates.env.globals["usuario_actual"] = usuario_actual

VALORES_PROBABILIDAD_RESIDUAL = {
    "RARA": 20,
    "IMPROBABLE": 40,
    "POSIBLE": 60,
    "PROBABLE": 80,
    "CASI_SEGURO": 100,
}

VALORES_IMPACTO_RESIDUAL = {
    "INSIGNIFICANTE": 20,
    "MENOR": 40,
    "MODERADO": 60,
    "MAYOR": 80,
    "CATASTROFICO": 100,
}

VALORES_SOLIDEZ_CONTROL = {
    "Muy baja": 10,
    "Baja": 30,
    "Media": 50,
    "Alta": 70,
    "Muy alta": 90,
}

CATEGORIAS_PROBABILIDAD_RESIDUAL = [
    (20, "Raro", 20),
    (40, "Improbable", 40),
    (60, "Posible", 60),
    (80, "Probable", 80),
    (100, "Casi seguro", 100),
]

CATEGORIAS_IMPACTO_RESIDUAL = [
    (20, "Insignificante", 20),
    (40, "Menor", 40),
    (60, "Moderado", 60),
    (80, "Mayor", 80),
    (100, "Catastrófico", 100),
]


def _porcentaje(valor):
    try:
        numero = float(valor or 0)
    except (TypeError, ValueError):
        numero = 0
    return max(0, min(100, numero))


def _redondear(valor):
    return round(float(valor or 0), 2)


def _categoria_residual(valor, categorias):
    valor = max(0, min(100, float(valor or 0)))
    for limite, etiqueta, categoria in categorias:
        if valor <= limite:
            return etiqueta, categoria
    return categorias[-1][1], categorias[-1][2]


def calcular_reporte_riesgo_inherente(riesgo):
    probabilidad_inicial = VALORES_PROBABILIDAD_RESIDUAL.get(riesgo.get("probabilidad"), 0)
    impacto_inicial = VALORES_IMPACTO_RESIDUAL.get(riesgo.get("impacto"), 0)
    riesgo_inherente = (probabilidad_inicial * impacto_inicial) / 100
    probabilidad_categoria, probabilidad_categorizada = _categoria_residual(
        probabilidad_inicial,
        CATEGORIAS_PROBABILIDAD_RESIDUAL,
    )
    impacto_categoria, impacto_categorizado = _categoria_residual(
        impacto_inicial,
        CATEGORIAS_IMPACTO_RESIDUAL,
    )
    riesgo_categorizado = (probabilidad_categorizada * impacto_categorizado) / 100

    return {
        "probabilidad_inicial": probabilidad_inicial,
        "impacto_inicial": impacto_inicial,
        "probabilidad_categoria": probabilidad_categoria,
        "probabilidad_categorizada": probabilidad_categorizada,
        "impacto_categoria": impacto_categoria,
        "impacto_categorizado": impacto_categorizado,
        "riesgo_inherente_exacto": _redondear(riesgo_inherente),
        "riesgo_inherente_categorizado": _redondear(riesgo_categorizado),
        "nivel": riesgo.get("nivel", ""),
    }


def calcular_reporte_riesgo_residual(riesgo, controles):
    probabilidad_inicial = VALORES_PROBABILIDAD_RESIDUAL.get(riesgo.get("probabilidad"), 0)
    impacto_inicial = VALORES_IMPACTO_RESIDUAL.get(riesgo.get("impacto"), 0)
    riesgo_inherente = (probabilidad_inicial * impacto_inicial) / 100

    controles_evaluados = []
    reducciones_probabilidad = []
    reducciones_impacto = []

    for control in controles:
        solidez = control.get("solidez_control") or "Media"
        solidez_valor = VALORES_SOLIDEZ_CONTROL.get(solidez, 50)
        maximo_baja_probabilidad = _porcentaje(control.get("maximo_baja_probabilidad", 100))
        maximo_baja_impacto = _porcentaje(control.get("maximo_baja_impacto", 100))
        mitigacion_probabilidad = _porcentaje(control.get("mitigacion_probabilidad"))
        mitigacion_impacto = _porcentaje(control.get("mitigacion_impacto"))
        capacidad_probabilidad = (maximo_baja_probabilidad * solidez_valor) / 100
        capacidad_impacto = (maximo_baja_impacto * solidez_valor) / 100
        reduccion_probabilidad = (maximo_baja_probabilidad * solidez_valor * mitigacion_probabilidad) / 10000
        reduccion_impacto = (maximo_baja_impacto * solidez_valor * mitigacion_impacto) / 10000

        if mitigacion_probabilidad > 0:
            reducciones_probabilidad.append(reduccion_probabilidad)
        if mitigacion_impacto > 0:
            reducciones_impacto.append(reduccion_impacto)

        control["solidez_valor"] = solidez_valor
        control["maximo_baja_probabilidad"] = _redondear(maximo_baja_probabilidad)
        control["maximo_baja_impacto"] = _redondear(maximo_baja_impacto)
        control["capacidad_real_probabilidad"] = _redondear(capacidad_probabilidad)
        control["capacidad_real_impacto"] = _redondear(capacidad_impacto)
        control["mitigacion_probabilidad"] = _redondear(mitigacion_probabilidad)
        control["mitigacion_impacto"] = _redondear(mitigacion_impacto)
        control["reduccion_real_probabilidad"] = _redondear(reduccion_probabilidad)
        control["reduccion_real_impacto"] = _redondear(reduccion_impacto)
        controles_evaluados.append({
            "nombre": control.get("nombre", ""),
            "solidez": solidez,
            "solidez_valor": solidez_valor,
            "maximo_baja_probabilidad": _redondear(maximo_baja_probabilidad),
            "maximo_baja_impacto": _redondear(maximo_baja_impacto),
            "capacidad_real_probabilidad": _redondear(capacidad_probabilidad),
            "capacidad_real_impacto": _redondear(capacidad_impacto),
            "mitigacion_probabilidad": _redondear(mitigacion_probabilidad),
            "mitigacion_impacto": _redondear(mitigacion_impacto),
            "reduccion_real_probabilidad": _redondear(reduccion_probabilidad),
            "reduccion_real_impacto": _redondear(reduccion_impacto),
        })

    promedio_probabilidad = sum(reducciones_probabilidad) / len(reducciones_probabilidad) if reducciones_probabilidad else 0
    promedio_impacto = sum(reducciones_impacto) / len(reducciones_impacto) if reducciones_impacto else 0
    probabilidad_residual = max(0, probabilidad_inicial - promedio_probabilidad)
    impacto_residual = max(0, impacto_inicial - promedio_impacto)
    riesgo_residual_exacto = (probabilidad_residual * impacto_residual) / 100
    probabilidad_categoria, probabilidad_residual_categorizada = _categoria_residual(
        probabilidad_residual,
        CATEGORIAS_PROBABILIDAD_RESIDUAL,
    )
    impacto_categoria, impacto_residual_categorizado = _categoria_residual(
        impacto_residual,
        CATEGORIAS_IMPACTO_RESIDUAL,
    )
    riesgo_residual_categorizado = (probabilidad_residual_categorizada * impacto_residual_categorizado) / 100

    return {
        "probabilidad_inicial": probabilidad_inicial,
        "impacto_inicial": impacto_inicial,
        "riesgo_inherente": _redondear(riesgo_inherente),
        "controles_evaluados": controles_evaluados,
        "total_controles_evaluados": len(controles_evaluados),
        "reduccion_promedio_probabilidad": _redondear(promedio_probabilidad),
        "reduccion_promedio_impacto": _redondear(promedio_impacto),
        "probabilidad_residual": _redondear(probabilidad_residual),
        "impacto_residual": _redondear(impacto_residual),
        "riesgo_residual_exacto": _redondear(riesgo_residual_exacto),
        "probabilidad_residual_categoria": probabilidad_categoria,
        "probabilidad_residual_categorizada": probabilidad_residual_categorizada,
        "impacto_residual_categoria": impacto_categoria,
        "impacto_residual_categorizado": impacto_residual_categorizado,
        "riesgo_residual_categorizado": _redondear(riesgo_residual_categorizado),
    }
def obtener_metricas_dashboard():
    metricas = {
        "grupos": 0,
        "procesos": 0,
        "riesgos": 0,
        "controles": 0,
        "niveles": [],
        "riesgos_recientes": [],
        "procesos_detalle": [],
        "riesgos_detalle": []
    }

    valores_impacto = {
        "INSIGNIFICANTE": 1,
        "MENOR": 2,
        "MODERADO": 3,
        "MAYOR": 4,
        "CATASTROFICO": 5
    }
    valores_probabilidad = {
        "RARA": 1,
        "IMPROBABLE": 2,
        "POSIBLE": 3,
        "PROBABLE": 4,
        "CASI_SEGURO": 5
    }

    db = conexion.conectar()
    if db == "":
        return metricas

    try:
        with db.cursor() as cursor:
            for clave, tabla in (
                ("grupos", "grupo"),
                ("procesos", "proceso"),
                ("riesgos", "riesgo"),
                ("controles", "control")
            ):
                cursor.execute(f"SELECT COUNT(*) AS total FROM {tabla}")
                fila = cursor.fetchone() or {}
                metricas[clave] = fila.get("total", 0)

            cursor.execute("""
                SELECT nivel, COUNT(*) AS total
                FROM riesgo
                GROUP BY nivel
                ORDER BY FIELD(nivel, 'MUY BAJO', 'BAJO', 'MEDIO', 'ALTO', 'EXTREMO')
            """)
            metricas["niveles"] = cursor.fetchall()

            cursor.execute("""
                SELECT
                    p.id_proceso,
                    p.nombre,
                    p.descripcion,
                    g.id_grupo,
                    g.nombre AS grupo_nombre,
                    g.descripcion AS grupo_descripcion
                FROM proceso p
                INNER JOIN grupo g ON g.id_grupo = p.id_grupo
                ORDER BY p.nombre ASC
            """)
            procesos = cursor.fetchall()

            cursor.execute("""
                SELECT
                    ug.id_grupo,
                    u.nombres_completo,
                    u.correo,
                    r.nombre AS rol_nombre
                FROM usuario_grupo ug
                INNER JOIN usuario u ON u.id = ug.id_usuario
                INNER JOIN rol r ON r.id_rol = ug.id_rol
                WHERE ug.estado = 'Activo'
                ORDER BY u.nombres_completo ASC
            """)
            integrantes_por_grupo = {}
            for integrante in cursor.fetchall():
                id_grupo = integrante["id_grupo"]
                integrantes_por_grupo.setdefault(id_grupo, []).append({
                    "nombre": integrante["nombres_completo"],
                    "correo": integrante["correo"],
                    "rol": integrante["rol_nombre"]
                })

            procesos_detalle = []
            for proceso in procesos:
                id_grupo = proceso["id_grupo"]
                procesos_detalle.append({
                    "id_proceso": proceso["id_proceso"],
                    "nombre": proceso["nombre"],
                    "descripcion": proceso["descripcion"] or "",
                    "grupo": {
                        "id_grupo": id_grupo,
                        "nombre": proceso["grupo_nombre"],
                        "descripcion": proceso["grupo_descripcion"] or "",
                        "integrantes": integrantes_por_grupo.get(id_grupo, [])
                    }
                })
            metricas["procesos_detalle"] = procesos_detalle

            cursor.execute("""
                SELECT id_riesgo, nombre, descripcion, impacto, frecuencia AS probabilidad, nivel
                FROM riesgo
                ORDER BY id_riesgo DESC
            """)
            riesgos = cursor.fetchall()

            cursor.execute("""
                SELECT
                    rp.id_riesgo,
                    p.id_proceso,
                    p.nombre AS proceso_nombre,
                    g.id_grupo,
                    g.nombre AS grupo_nombre
                FROM riesgo_proceso rp
                INNER JOIN proceso p ON p.id_proceso = rp.id_proceso
                INNER JOIN grupo g ON g.id_grupo = p.id_grupo
                ORDER BY p.nombre ASC
            """)
            procesos_por_riesgo = {}
            for fila in cursor.fetchall():
                procesos_por_riesgo.setdefault(fila["id_riesgo"], []).append({
                    "id_proceso": fila["id_proceso"],
                    "nombre": fila["proceso_nombre"],
                    "id_grupo": fila["id_grupo"],
                    "grupo_nombre": fila["grupo_nombre"]
                })

            cursor.execute("""
                SELECT
                    c.id_control,
                    c.id_riesgo,
                    c.nombre,
                    c.descripcion,
                    c.tipo,
                    c.solidez_control,
                    CASE r.frecuencia
                        WHEN 'RARA' THEN 20
                        WHEN 'IMPROBABLE' THEN 40
                        WHEN 'POSIBLE' THEN 60
                        WHEN 'PROBABLE' THEN 80
                        WHEN 'CASI_SEGURO' THEN 100
                        ELSE 100
                    END AS maximo_baja_probabilidad,
                    CASE r.impacto
                        WHEN 'INSIGNIFICANTE' THEN 20
                        WHEN 'MENOR' THEN 40
                        WHEN 'MODERADO' THEN 60
                        WHEN 'MAYOR' THEN 80
                        WHEN 'CATASTROFICO' THEN 100
                        ELSE 100
                    END AS maximo_baja_impacto,
                    c.mitigacion_probabilidad,
                    c.mitigacion_impacto,
                    c.estado
                FROM control c
                INNER JOIN riesgo r ON r.id_riesgo = c.id_riesgo
                ORDER BY c.id_control DESC
            """)
            controles_por_riesgo = {}
            for control in cursor.fetchall():
                controles_por_riesgo.setdefault(control["id_riesgo"], []).append({
                    "id_control": control["id_control"],
                    "nombre": control["nombre"],
                    "descripcion": control["descripcion"] or "",
                    "tipo": control["tipo"],
                    "solidez_control": control["solidez_control"],
                    "maximo_baja_probabilidad": control["maximo_baja_probabilidad"],
                    "maximo_baja_impacto": control["maximo_baja_impacto"],
                    "mitigacion_probabilidad": control["mitigacion_probabilidad"],
                    "mitigacion_impacto": control["mitigacion_impacto"],
                    "estado": control["estado"]
                })

            riesgos_detalle = []
            for riesgo in riesgos:
                procesos_riesgo = procesos_por_riesgo.get(riesgo["id_riesgo"], [])
                grupos = []
                grupos_vistos = set()
                for proceso in procesos_riesgo:
                    id_grupo = proceso["id_grupo"]
                    if id_grupo in grupos_vistos:
                        continue
                    grupos_vistos.add(id_grupo)
                    grupos.append({
                        "id_grupo": id_grupo,
                        "nombre": proceso["grupo_nombre"],
                        "integrantes": integrantes_por_grupo.get(id_grupo, [])
                    })

                impacto_valor = valores_impacto.get(riesgo["impacto"], 0)
                probabilidad_valor = valores_probabilidad.get(riesgo["probabilidad"], 0)
                puntaje = impacto_valor * probabilidad_valor
                controles_riesgo = controles_por_riesgo.get(riesgo["id_riesgo"], [])
                reporte_inherente = calcular_reporte_riesgo_inherente(riesgo)
                reporte_residual = calcular_reporte_riesgo_residual(riesgo, controles_riesgo)
                riesgos_detalle.append({
                    "id_riesgo": riesgo["id_riesgo"],
                    "codigo": f"RSK-{riesgo['id_riesgo']:03d}",
                    "nombre": riesgo["nombre"],
                    "descripcion": riesgo["descripcion"] or "",
                    "impacto": riesgo["impacto"],
                    "probabilidad": riesgo["probabilidad"],
                    "nivel": riesgo["nivel"],
                    "puntaje": puntaje,
                    "impacto_valor": impacto_valor,
                    "probabilidad_valor": probabilidad_valor,
                    "procesos": procesos_riesgo,
                    "grupos": grupos,
                    "controles": controles_riesgo,
                    "riesgo_inherente": reporte_inherente,
                    "riesgo_residual": reporte_residual
                })

            metricas["riesgos_detalle"] = riesgos_detalle
            metricas["riesgos_recientes"] = riesgos_detalle[:5]
    finally:
        db.close()

    return metricas

def _xml_text(value):
    return html.escape(str(value or ""), quote=True)


def _excel_cell(columna, fila, valor, estilo=0):
    referencia = f"{columna}{fila}"
    if isinstance(valor, (int, float)):
        return f'<c r="{referencia}" s="{estilo}"><v>{valor}</v></c>'
    return f'<c r="{referencia}" s="{estilo}" t="inlineStr"><is><t>{_xml_text(valor)}</t></is></c>'


def _excel_row(fila, celdas):
    contenido = "".join(_excel_cell(columna, fila, valor, estilo) for columna, valor, estilo in celdas)
    return f'<row r="{fila}">{contenido}</row>'


def _nivel_estilo(nivel):
    return {
        "MUY BAJO": 4,
        "BAJO": 5,
        "MEDIO": 6,
        "ALTO": 7,
        "EXTREMO": 8,
    }.get(nivel, 0)


def _nivel_estilo_marcado(nivel):
    return {
        "MUY BAJO": 10,
        "BAJO": 11,
        "MEDIO": 12,
        "ALTO": 13,
        "EXTREMO": 14,
    }.get(nivel, _nivel_estilo(nivel))


def _texto_riesgo(valor):
    return str(valor or "-").replace("_", " ").title()


def _nivel_desde_puntaje(puntaje):
    if puntaje == 1:
        return "MUY BAJO"
    if puntaje <= 4:
        return "BAJO"
    if puntaje <= 9:
        return "MEDIO"
    if puntaje <= 16:
        return "ALTO"
    return "EXTREMO"


def construir_excel_detalle_riesgo(riesgo):
    filas = []
    merges = ["A1:H1", "A3:H3", "A10:H10", "A20:H20"]

    residual = riesgo.get("riesgo_residual", {})
    inherente = riesgo.get("riesgo_inherente", {})
    impacto_texto = _texto_riesgo(riesgo.get("impacto"))
    probabilidad_texto = _texto_riesgo(riesgo.get("probabilidad"))
    ubicacion = f"Probabilidad {riesgo.get('probabilidad_valor', '-')}, Impacto {riesgo.get('impacto_valor', '-')}, Puntaje {riesgo.get('puntaje', '-')}"

    filas.append(_excel_row(1, [("A", "MAGERISK - Reporte ejecutivo de riesgo", 1)]))
    filas.append(_excel_row(2, [("A", "Exportación del detalle, evaluación inherente, mapa de calor y controles asociados.", 15)]))
    filas.append(_excel_row(3, [("A", "Resumen ejecutivo", 2)]))
    filas.append(_excel_row(4, [("A", "Código", 3), ("B", riesgo["codigo"], 16), ("C", "Riesgo", 3), ("D", riesgo["nombre"], 16), ("F", "Nivel", 3), ("G", riesgo["nivel"], _nivel_estilo(riesgo["nivel"]))]))
    filas.append(_excel_row(5, [("A", "Impacto", 3), ("B", impacto_texto, 16), ("C", "Probabilidad", 3), ("D", probabilidad_texto, 16), ("F", "Puntaje matriz", 3), ("G", riesgo["puntaje"], 16)]))
    filas.append(_excel_row(6, [("A", "Descripción", 3), ("B", riesgo["descripcion"] or "Sin descripción registrada.", 16)]))
    merges.append("B6:H6")
    filas.append(_excel_row(7, [("A", "Riesgo inherente", 3), ("B", inherente.get("riesgo_inherente_exacto", residual.get("riesgo_inherente", 0)), 16), ("C", "Prob. inicial", 3), ("D", f"{inherente.get('probabilidad_inicial', residual.get('probabilidad_inicial', 0))}%", 16), ("F", "Impacto inicial", 3), ("G", f"{inherente.get('impacto_inicial', residual.get('impacto_inicial', 0))}%", 16)]))
    filas.append(_excel_row(8, [("A", "Ubicación", 3), ("B", ubicacion, 16), ("C", "Actividades", 3), ("D", len(riesgo.get("procesos", [])), 16), ("F", "Controles", 3), ("G", residual.get("total_controles_evaluados", len(riesgo.get("controles", []))), 16)]))

    filas.append(_excel_row(10, [("A", "Mapa de calor 5 x 5 y ubicación del riesgo", 2)]))
    filas.append(_excel_row(11, [("A", "La celda marcada como R.I. muestra el punto exacto del riesgo evaluado.", 15)]))
    filas.append(_excel_row(12, [("A", "Prob. \\ Impacto", 3), ("B", "1 Ins.", 3), ("C", "2 Men.", 3), ("D", "3 Mod.", 3), ("E", "4 May.", 3), ("F", "5 Cat.", 3), ("H", "Leyenda", 3)]))
    etiquetas_probabilidad = ["5 Casi seguro", "4 Probable", "3 Posible", "2 Improbable", "1 Raro"]
    for indice_fila, probabilidad in enumerate(range(5, 0, -1), start=13):
        celdas = [("A", etiquetas_probabilidad[indice_fila - 13], 3)]
        for impacto in range(1, 6):
            puntaje = probabilidad * impacto
            nivel = _nivel_desde_puntaje(puntaje)
            es_riesgo = impacto == riesgo["impacto_valor"] and probabilidad == riesgo["probabilidad_valor"]
            valor = f"R.I. {puntaje}" if es_riesgo else puntaje
            estilo = _nivel_estilo_marcado(nivel) if es_riesgo else _nivel_estilo(nivel)
            celdas.append((chr(65 + impacto), valor, estilo))
        filas.append(_excel_row(indice_fila, celdas))
    filas.append(_excel_row(13, [("H", "Muy bajo = 1", 4)]))
    filas.append(_excel_row(14, [("H", "Bajo = 2-4", 5)]))
    filas.append(_excel_row(15, [("H", "Medio = 5-9", 6)]))
    filas.append(_excel_row(16, [("H", "Alto = 10-16", 7)]))
    filas.append(_excel_row(17, [("H", "Extremo = 17-25", 8)]))
    filas.append(_excel_row(18, [("A", "Ubicación interpretada", 3), ("B", f"{probabilidad_texto} / {impacto_texto}", 16), ("D", "Nivel", 3), ("E", riesgo["nivel"], _nivel_estilo(riesgo["nivel"]))]))

    filas.append(_excel_row(20, [("A", "Actividades y responsables", 2)]))
    filas.append(_excel_row(21, [("A", "Actividad", 3), ("B", "Grupo", 3), ("C", "Responsables", 3)]))
    fila_actual = 22
    if riesgo["procesos"]:
        grupos = {grupo["id_grupo"]: grupo for grupo in riesgo["grupos"]}
        for proceso in riesgo["procesos"]:
            grupo = grupos.get(proceso["id_grupo"], {})
            integrantes = grupo.get("integrantes", [])
            responsables = "; ".join(f"{item['nombre']} ({item['rol']})" for item in integrantes) or "Sin integrantes activos"
            filas.append(_excel_row(fila_actual, [("A", proceso["nombre"], 0), ("B", proceso["grupo_nombre"], 0), ("C", responsables, 0)]))
            fila_actual += 1
    else:
        filas.append(_excel_row(fila_actual, [("A", "Sin actividades asociadas", 0)]))
        fila_actual += 1

    fila_actual += 1
    merges.append(f"A{fila_actual}:H{fila_actual}")
    filas.append(_excel_row(fila_actual, [("A", "Reporte de riesgo inherente", 2)]))
    fila_actual += 1
    filas.append(_excel_row(fila_actual, [("A", "Métrica", 3), ("B", "Valor", 3), ("C", "Detalle", 3)]))
    fila_actual += 1
    filas.extend([
        _excel_row(fila_actual, [("A", "Probabilidad inicial", 0), ("B", inherente.get("probabilidad_inicial", residual.get("probabilidad_inicial", 0)), 16), ("C", inherente.get("probabilidad_categoria", "-"), 16)]),
        _excel_row(fila_actual + 1, [("A", "Impacto inicial", 0), ("B", inherente.get("impacto_inicial", residual.get("impacto_inicial", 0)), 16), ("C", inherente.get("impacto_categoria", "-"), 16)]),
        _excel_row(fila_actual + 2, [("A", "Riesgo inherente exacto", 0), ("B", inherente.get("riesgo_inherente_exacto", residual.get("riesgo_inherente", 0)), 16), ("C", "Probabilidad × Impacto / 100", 16)]),
        _excel_row(fila_actual + 3, [("A", "Riesgo inherente categorizado", 0), ("B", inherente.get("riesgo_inherente_categorizado", residual.get("riesgo_inherente", 0)), 16), ("C", f"{inherente.get('probabilidad_categoria', '-')} / {inherente.get('impacto_categoria', '-')}", 16)]),
        _excel_row(fila_actual + 4, [("A", "Nivel matriz 5x5", 0), ("B", inherente.get("nivel", riesgo.get("nivel", "-")), _nivel_estilo(riesgo.get("nivel", "")))]),
    ])
    fila_actual += 6

    merges.append(f"A{fila_actual}:H{fila_actual}")
    filas.append(_excel_row(fila_actual, [("A", "Controles asociados", 2)]))
    fila_actual += 1
    filas.append(_excel_row(fila_actual, [("A", "Control", 3), ("B", "Tipo", 3), ("C", "Solidez", 3), ("D", "Máx. Prob./Imp.", 3), ("E", "Mit. Prob./Imp.", 3), ("F", "Estado", 3), ("G", "Descripción", 3)]))
    fila_actual += 1
    if riesgo["controles"]:
        for control in riesgo["controles"]:
            filas.append(_excel_row(fila_actual, [("A", control["nombre"], 0), ("B", control["tipo"], 0), ("C", control["solidez_control"], 0), ("D", f"{control.get('maximo_baja_probabilidad', 100)} / {control.get('maximo_baja_impacto', 100)}", 0), ("E", f"{control.get('mitigacion_probabilidad', 0)} / {control.get('mitigacion_impacto', 0)}", 0), ("F", control["estado"], 0), ("G", control["descripcion"] or "Sin descripción", 0)]))
            fila_actual += 1
    else:
        filas.append(_excel_row(fila_actual, [("A", "Este riesgo aún no tiene controles asociados.", 0)]))
        fila_actual += 1

    fila_actual += 1
    merges.append(f"A{fila_actual}:H{fila_actual}")
    filas.append(_excel_row(fila_actual, [("A", "Reporte de riesgo residual", 2)]))
    fila_actual += 1
    filas.append(_excel_row(fila_actual, [("A", "Métrica", 3), ("B", "Valor", 3), ("C", "Detalle", 3)]))
    fila_actual += 1
    filas.extend([
        _excel_row(fila_actual, [("A", "Controles evaluados", 0), ("B", residual.get("total_controles_evaluados", 0), 16)]),
        _excel_row(fila_actual + 1, [("A", "Reducción promedio de probabilidad", 0), ("B", residual.get("reduccion_promedio_probabilidad", 0), 16)]),
        _excel_row(fila_actual + 2, [("A", "Reducción promedio de impacto", 0), ("B", residual.get("reduccion_promedio_impacto", 0), 16)]),
        _excel_row(fila_actual + 3, [("A", "Probabilidad residual", 0), ("B", residual.get("probabilidad_residual", 0), 16), ("C", residual.get("probabilidad_residual_categoria", "-"), 16)]),
        _excel_row(fila_actual + 4, [("A", "Impacto residual", 0), ("B", residual.get("impacto_residual", 0), 16), ("C", residual.get("impacto_residual_categoria", "-"), 16)]),
        _excel_row(fila_actual + 5, [("A", "Riesgo residual exacto", 0), ("B", residual.get("riesgo_residual_exacto", 0), 16)]),
        _excel_row(fila_actual + 6, [("A", "Riesgo residual categorizado", 0), ("B", residual.get("riesgo_residual_categorizado", 0), 16), ("C", f"{residual.get('probabilidad_residual_categoria', '-')} / {residual.get('impacto_residual_categoria', '-')}", 16)]),
    ])
    fila_actual += 8

    merges.append(f"A{fila_actual}:H{fila_actual}")
    filas.append(_excel_row(fila_actual, [("A", "Controles evaluados para residual", 2)]))
    fila_actual += 1
    filas.append(_excel_row(fila_actual, [("A", "Control", 3), ("B", "Máx. prob/imp", 3), ("C", "Solidez aplicada", 3), ("D", "Mit. prob/imp", 3), ("E", "Red. prob.", 3), ("F", "Red. impacto", 3)]))
    fila_actual += 1
    controles_residual = residual.get("controles_evaluados", [])
    if controles_residual:
        for control in controles_residual:
            filas.append(_excel_row(fila_actual, [("A", control.get("nombre", ""), 0), ("B", f"{control.get('maximo_baja_probabilidad', 0)} / {control.get('maximo_baja_impacto', 0)}", 0), ("C", f"{control.get('solidez', '')} ({control.get('solidez_valor', 0)}%) = {control.get('capacidad_real_probabilidad', 0)} / {control.get('capacidad_real_impacto', 0)}", 0), ("D", f"{control.get('mitigacion_probabilidad', 0)} / {control.get('mitigacion_impacto', 0)}", 0), ("E", control.get("reduccion_real_probabilidad", 0), 0), ("F", control.get("reduccion_real_impacto", 0), 0)]))
            fila_actual += 1
    else:
        filas.append(_excel_row(fila_actual, [("A", "Sin controles evaluados", 0)]))

    merges_xml = ''.join(f'<mergeCell ref="{merge}"/>' for merge in merges)
    hoja = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheetViews><sheetView workbookViewId="0" showGridLines="0"/></sheetViews>
<cols><col min="1" max="1" width="24"/><col min="2" max="2" width="18"/><col min="3" max="3" width="18"/><col min="4" max="4" width="18"/><col min="5" max="5" width="18"/><col min="6" max="6" width="18"/><col min="7" max="7" width="28"/><col min="8" max="8" width="24"/></cols>
<sheetData>{''.join(filas)}</sheetData>
<mergeCells count="{len(merges)}">{merges_xml}</mergeCells>
</worksheet>'''
    estilos = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="5"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="18"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FF111827"/><name val="Calibri"/></font><font><i/><sz val="10"/><color rgb="FF64748B"/><name val="Calibri"/></font></fonts>
<fills count="11"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF172033"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFD9EAD3"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF22C55E"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFBBF24"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFF97316"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFEF4444"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF334155"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFF8FAFC"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFF7ED"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="3"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FFE2E8F0"/></left><right style="thin"><color rgb="FFE2E8F0"/></right><top style="thin"><color rgb="FFE2E8F0"/></top><bottom style="thin"><color rgb="FFE2E8F0"/></bottom><diagonal/></border><border><left style="thick"><color rgb="FF111827"/></left><right style="thick"><color rgb="FF111827"/></right><top style="thick"><color rgb="FF111827"/></top><bottom style="thick"><color rgb="FF111827"/></bottom><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="17"><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="8" borderId="1" xfId="0" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center"/></xf><xf numFmtId="0" fontId="3" fillId="3" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="3" fillId="5" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="6" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="7" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="9" borderId="1" xfId="0" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="3" fillId="3" borderId="2" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="4" borderId="2" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="3" fillId="5" borderId="2" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="6" borderId="2" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="2" fillId="7" borderId="2" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf><xf numFmtId="0" fontId="4" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="0" fillId="10" borderId="1" xfId="0" applyFill="1" applyBorder="1"/></cellXfs>
</styleSheet>'''
    archivos = {
        "[Content_Types].xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>''',
        "_rels/.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''',
        "xl/workbook.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Detalle del riesgo" sheetId="1" r:id="rId1"/></sheets></workbook>''',
        "xl/_rels/workbook.xml.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>''',
        "xl/worksheets/sheet1.xml": hoja,
        "xl/styles.xml": estilos,
    }
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as paquete:
        for nombre, contenido in archivos.items():
            paquete.writestr(nombre, contenido)
    return salida.getvalue()


def construir_excel_dashboard(datos):
    filas = []
    merges = ["A1:O1", "A3:O3", "A9:O9"]
    fila = 1

    filas.append(_excel_row(fila, [("A", "MAGERISK - Dashboard detallado", 1)]))
    fila += 1
    filas.append(_excel_row(fila, [("A", "Exportación consolidada de riesgos, controles, responsables, riesgo inherente y residual.", 4)]))
    fila += 2
    filas.append(_excel_row(fila, [("A", "Resumen", 2)]))
    fila += 1
    filas.append(_excel_row(fila, [
        ("A", "Riesgos", 3), ("B", datos.get("riesgos", 0), 0),
        ("D", "Controles", 3), ("E", datos.get("controles", 0), 0),
        ("G", "Actividades", 3), ("H", datos.get("procesos", 0), 0),
        ("J", "Grupos", 3), ("K", datos.get("grupos", 0), 0),
    ]))
    fila += 2
    filas.append(_excel_row(fila, [("A", "Distribución por nivel", 2)]))
    fila += 1
    filas.append(_excel_row(fila, [("A", "Nivel", 3), ("B", "Total", 3)]))
    fila += 1
    for nivel in datos.get("niveles", []):
        filas.append(_excel_row(fila, [("A", nivel.get("nivel", "-"), _nivel_estilo(nivel.get("nivel", ""))), ("B", nivel.get("total", 0), 0)]))
        fila += 1

    fila += 1
    merges.append(f"A{fila}:O{fila}")
    filas.append(_excel_row(fila, [("A", "Detalle completo", 2)]))
    fila += 1
    encabezados = [
        "Código", "Riesgo", "Nivel", "Probabilidad", "Impacto", "Puntaje",
        "Inherente", "Prob. residual", "Impacto residual", "Residual",
        "Actividades", "Responsables", "Controles", "Red. prob.", "Red. impacto"
    ]
    filas.append(_excel_row(fila, [(chr(65 + indice), titulo, 3) for indice, titulo in enumerate(encabezados)]))
    fila += 1

    for riesgo in datos.get("riesgos_detalle", []):
        inherente = riesgo.get("riesgo_inherente", {})
        residual = riesgo.get("riesgo_residual", {})
        procesos = "; ".join(proceso.get("nombre", "") for proceso in riesgo.get("procesos", [])) or "Sin actividades"
        responsables = []
        for grupo in riesgo.get("grupos", []):
            for integrante in grupo.get("integrantes", []):
                responsables.append(f"{integrante.get('nombre', '')} ({integrante.get('rol', '')})")
        controles = "; ".join(control.get("nombre", "") for control in riesgo.get("controles", [])) or "Sin controles"
        filas.append(_excel_row(fila, [
            ("A", riesgo.get("codigo", ""), 0),
            ("B", riesgo.get("nombre", ""), 0),
            ("C", riesgo.get("nivel", ""), _nivel_estilo(riesgo.get("nivel", ""))),
            ("D", _texto_riesgo(riesgo.get("probabilidad")), 0),
            ("E", _texto_riesgo(riesgo.get("impacto")), 0),
            ("F", riesgo.get("puntaje", 0), 0),
            ("G", inherente.get("riesgo_inherente_exacto", residual.get("riesgo_inherente", 0)), 0),
            ("H", residual.get("probabilidad_residual", 0), 0),
            ("I", residual.get("impacto_residual", 0), 0),
            ("J", residual.get("riesgo_residual_exacto", 0), 0),
            ("K", procesos, 0),
            ("L", "; ".join(responsables) or "Sin responsables", 0),
            ("M", controles, 0),
            ("N", residual.get("reduccion_promedio_probabilidad", 0), 0),
            ("O", residual.get("reduccion_promedio_impacto", 0), 0),
        ]))
        fila += 1

    merges_xml = ''.join(f'<mergeCell ref="{merge}"/>' for merge in merges)
    hoja = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheetViews><sheetView workbookViewId="0" showGridLines="0"/></sheetViews>
<cols><col min="1" max="1" width="14"/><col min="2" max="2" width="32"/><col min="3" max="3" width="14"/><col min="4" max="5" width="18"/><col min="6" max="10" width="16"/><col min="11" max="13" width="38"/><col min="14" max="15" width="16"/></cols>
<sheetData>{''.join(filas)}</sheetData>
<mergeCells count="{len(merges)}">{merges_xml}</mergeCells>
</worksheet>'''
    estilos = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="4"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="18"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font><font><i/><sz val="10"/><color rgb="FF64748B"/><name val="Calibri"/></font></fonts>
<fills count="9"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF111827"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFF8FAFC"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFD9EAD3"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF22C55E"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFBBF24"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFF97316"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFEF4444"/></patternFill></fill></fills>
<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style="thin"><color rgb="FFE2E8F0"/></left><right style="thin"><color rgb="FFE2E8F0"/></right><top style="thin"><color rgb="FFE2E8F0"/></top><bottom style="thin"><color rgb="FFE2E8F0"/></bottom><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="9"><xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment horizontal="center"/></xf><xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0" applyFill="1"/><xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0" applyFill="1"/><xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="2" fillId="5" borderId="1" xfId="0" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="0" fillId="6" borderId="1" xfId="0" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="2" fillId="7" borderId="1" xfId="0" applyFill="1" applyBorder="1"/><xf numFmtId="0" fontId="2" fillId="8" borderId="1" xfId="0" applyFill="1" applyBorder="1"/></cellXfs>
</styleSheet>'''
    archivos = {
        "[Content_Types].xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>''',
        "_rels/.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''',
        "xl/workbook.xml": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Dashboard" sheetId="1" r:id="rId1"/></sheets></workbook>''',
        "xl/_rels/workbook.xml.rels": '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>''',
        "xl/worksheets/sheet1.xml": hoja,
        "xl/styles.xml": estilos,
    }
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as paquete:
        for nombre, contenido in archivos.items():
            paquete.writestr(nombre, contenido)
    return salida.getvalue()
app.mount("/static", StaticFiles(directory=str(BASE_DIR.parent / "static")), name="static")
app.add_middleware(
    SessionMiddleware,
    secret_key="mi_clave_super_secreta"
)

@app.get("/")
def inicio(request:Request):
    return RedirectResponse(
        "/dashboard",
        status_code=302
    )

@app.get('/dashboard')
def dashboard(request: Request):

    usuario = usuario_actual(request)
    mensaje = request.session.pop("mensaje", None)

    return templates.TemplateResponse(
        request=request,
        name="/maestras/dashboard.html",
        context={
            
            "usuario": usuario,
            "mensaje": mensaje,
            "metricas": obtener_metricas_dashboard()
        }
    )


@app.get('/dashboard/exportar_excel')
def exportar_dashboard_excel(request: Request):
    datos = obtener_metricas_dashboard()
    id_riesgo = request.query_params.get("id_riesgo")
    id_proceso = request.query_params.get("id_proceso")

    riesgos_exportar = datos.get("riesgos_detalle", [])
    nombre_archivo = "dashboard_riesgos.xlsx"

    if id_riesgo:
        riesgos_exportar = [
            riesgo for riesgo in riesgos_exportar
            if str(riesgo.get("id_riesgo")) == str(id_riesgo)
        ]
        if riesgos_exportar:
            nombre_base = re.sub(
                r"[^A-Za-z0-9_-]+",
                "_",
                riesgos_exportar[0].get("codigo", "riesgo") + "_" + riesgos_exportar[0].get("nombre", "")
            ).strip("_")
            nombre_archivo = f"{nombre_base or 'riesgo'}.xlsx"
    elif id_proceso:
        riesgos_exportar = [
            riesgo for riesgo in riesgos_exportar
            if any(str(proceso.get("id_proceso")) == str(id_proceso) for proceso in riesgo.get("procesos", []))
        ]
        nombre_archivo = f"dashboard_actividad_{id_proceso}.xlsx"

    niveles_exportar = []
    for nivel in ("MUY BAJO", "BAJO", "MEDIO", "ALTO", "EXTREMO"):
        total = sum(1 for riesgo in riesgos_exportar if riesgo.get("nivel") == nivel)
        if total:
            niveles_exportar.append({"nivel": nivel, "total": total})

    datos = {
        **datos,
        "riesgos": len(riesgos_exportar),
        "controles": sum(len(riesgo.get("controles", [])) for riesgo in riesgos_exportar),
        "niveles": niveles_exportar,
        "riesgos_detalle": riesgos_exportar,
    }
    contenido = construir_excel_dashboard(datos)
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre_archivo}"'
        }
    )


@app.get('/dashboard/riesgo/{id_riesgo}/exportar_excel')
def exportar_detalle_riesgo_excel(id_riesgo: int, request: Request):
    datos = obtener_metricas_dashboard()
    riesgo = next(
        (item for item in datos["riesgos_detalle"] if item["id_riesgo"] == id_riesgo),
        None
    )
    if riesgo is None:
        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    contenido = construir_excel_detalle_riesgo(riesgo)
    nombre_base = re.sub(r"[^A-Za-z0-9_-]+", "_", riesgo["codigo"] + "_" + riesgo["nombre"]).strip("_")
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre_base}.xlsx"'
        }
    )
procesos.rutas(app, templates)
usuario.rutas(app, templates)
riesgos.rutas(app, templates)
controles.rutas(app, templates)
