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
                    id_control,
                    id_riesgo,
                    nombre,
                    descripcion,
                    tipo,
                    solidez_control,
                    estado
                FROM control
                ORDER BY id_control DESC
            """)
            controles_por_riesgo = {}
            for control in cursor.fetchall():
                controles_por_riesgo.setdefault(control["id_riesgo"], []).append({
                    "id_control": control["id_control"],
                    "nombre": control["nombre"],
                    "descripcion": control["descripcion"] or "",
                    "tipo": control["tipo"],
                    "solidez_control": control["solidez_control"],
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
                    "controles": controles_por_riesgo.get(riesgo["id_riesgo"], [])
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
    merges = ["A1:F1", "A3:F3", "A9:F9", "A17:F17", "A25:F25"]

    filas.append(_excel_row(1, [("A", "MAGERISK - Detalle del riesgo", 1)]))
    filas.append(_excel_row(3, [("A", "Resumen ejecutivo", 2)]))
    filas.append(_excel_row(4, [("A", "Código", 3), ("B", riesgo["codigo"], 0), ("C", "Riesgo", 3), ("D", riesgo["nombre"], 0)]))
    filas.append(_excel_row(5, [("A", "Nivel", 3), ("B", riesgo["nivel"], _nivel_estilo(riesgo["nivel"])), ("C", "Puntaje", 3), ("D", riesgo["puntaje"], 0)]))
    filas.append(_excel_row(6, [("A", "Impacto", 3), ("B", riesgo["impacto"], 0), ("C", "Probabilidad", 3), ("D", riesgo["probabilidad"], 0)]))
    filas.append(_excel_row(7, [("A", "Descripción", 3), ("B", riesgo["descripcion"] or "Sin descripción registrada.", 0)]))

    filas.append(_excel_row(9, [("A", "Mapa de calor 5 x 5", 2)]))
    filas.append(_excel_row(10, [("B", "1 Ins.", 3), ("C", "2 Men.", 3), ("D", "3 Mod.", 3), ("E", "4 May.", 3), ("F", "5 Cat.", 3)]))
    etiquetas_probabilidad = ["5 Casi seguro", "4 Probable", "3 Posible", "2 Improbable", "1 Raro"]
    for indice_fila, probabilidad in enumerate(range(5, 0, -1), start=11):
        celdas = [("A", etiquetas_probabilidad[indice_fila - 11], 3)]
        for impacto in range(1, 6):
            puntaje = probabilidad * impacto
            nivel = _nivel_desde_puntaje(puntaje)
            valor = f"{puntaje} R.I." if impacto == riesgo["impacto_valor"] and probabilidad == riesgo["probabilidad_valor"] else puntaje
            celdas.append((chr(65 + impacto), valor, _nivel_estilo(nivel)))
        filas.append(_excel_row(indice_fila, celdas))

    filas.append(_excel_row(17, [("A", "Procesos y responsables", 2)]))
    filas.append(_excel_row(18, [("A", "Proceso", 3), ("B", "Grupo", 3), ("C", "Responsables", 3)]))
    fila_actual = 19
    if riesgo["procesos"]:
        grupos = {grupo["id_grupo"]: grupo for grupo in riesgo["grupos"]}
        for proceso in riesgo["procesos"]:
            grupo = grupos.get(proceso["id_grupo"], {})
            integrantes = grupo.get("integrantes", [])
            responsables = "; ".join(f"{item['nombre']} ({item['rol']})" for item in integrantes) or "Sin integrantes activos"
            filas.append(_excel_row(fila_actual, [("A", proceso["nombre"], 0), ("B", proceso["grupo_nombre"], 0), ("C", responsables, 0)]))
            fila_actual += 1
    else:
        filas.append(_excel_row(fila_actual, [("A", "Sin procesos asociados", 0)]))
        fila_actual += 1

    fila_actual += 1
    merges.append(f"A{fila_actual}:F{fila_actual}")
    filas.append(_excel_row(fila_actual, [("A", "Controles asociados", 2)]))
    fila_actual += 1
    filas.append(_excel_row(fila_actual, [("A", "Control", 3), ("B", "Tipo", 3), ("C", "Solidez", 3), ("D", "Estado", 3), ("E", "Descripcion", 3)]))
    fila_actual += 1
    if riesgo["controles"]:
        for control in riesgo["controles"]:
            filas.append(_excel_row(fila_actual, [
                ("A", control["nombre"], 0),
                ("B", control["tipo"], 0),
                ("C", control["solidez_control"], 0),
                ("D", control["estado"], 0),
                ("E", control["descripcion"] or "Sin descripcion", 0),
            ]))
            fila_actual += 1
    else:
        filas.append(_excel_row(fila_actual, [("A", "Este riesgo aún no tiene controles asociados.", 0)]))

    merges_xml = ''.join(f'<mergeCell ref="{merge}"/>' for merge in merges)
    hoja = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<cols><col min="1" max="1" width="22"/><col min="2" max="2" width="22"/><col min="3" max="3" width="22"/><col min="4" max="4" width="22"/><col min="5" max="5" width="18"/><col min="6" max="6" width="48"/></cols>
<sheetData>{''.join(filas)}</sheetData>
<mergeCells count="{len(merges)}">{merges_xml}</mergeCells>
</worksheet>'''

    estilos = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="3"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="16"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>
<fills count="9"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF172033"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFD9EAD3"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF22C55E"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFBBF24"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFF97316"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFEF4444"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FF334155"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="10"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyAlignment="1"><alignment horizontal="center"/></xf><xf numFmtId="0" fontId="2" fillId="8" borderId="0" xfId="0" applyFill="1"/><xf numFmtId="0" fontId="2" fillId="2" borderId="0" xfId="0" applyFill="1"/><xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1"/><xf numFmtId="0" fontId="2" fillId="4" borderId="0" xfId="0" applyFill="1"/><xf numFmtId="0" fontId="0" fillId="5" borderId="0" xfId="0" applyFill="1"/><xf numFmtId="0" fontId="2" fillId="6" borderId="0" xfId="0" applyFill="1"/><xf numFmtId="0" fontId="2" fillId="7" borderId="0" xfId="0" applyFill="1"/><xf numFmtId="0" fontId="0" fillId="8" borderId="0" xfId="0" applyFill="1"/></cellXfs>
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
