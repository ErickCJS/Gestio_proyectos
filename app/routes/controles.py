import json
import os
from pathlib import Path

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse
try:
    from .. import conexion
    from ..ia_config import cargar_configuracion_ia as cargar_configuracion_ia_global
    from ..ia_config import cargar_configuraciones_ia, detalle_error_ia
except ImportError:
    import conexion
    from ia_config import cargar_configuracion_ia as cargar_configuracion_ia_global
    from ia_config import cargar_configuraciones_ia, detalle_error_ia


def rutas(app, templates):
    def set_flash(request, tipo, texto):
        request.session["flash"] = {
            "tipo": tipo,
            "texto": texto,
        }

    tipos_control = {"Preventivo", "Detectivo", "Correctivo"}
    solidez_opciones = {"Muy baja", "Baja", "Media", "Alta", "Muy alta"}

    def porcentaje_formulario(valor, defecto=0):
        try:
            numero = float(valor if valor not in (None, "") else defecto)
        except (TypeError, ValueError):
            numero = defecto
        return max(0, min(100, numero))

    def cargar_valor_env(nombre):
        valor = os.getenv(nombre)
        if valor:
            return valor

        env_path = Path(__file__).resolve().parents[2] / ".env"
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

    def cargar_configuracion_ia():
        return cargar_configuracion_ia_global()

    def texto_corto(valor, maximo):
        texto = " ".join(str(valor or "").split())
        return texto[:maximo]

    def cargar_riesgos(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id_riesgo,
                    nombre,
                    descripcion,
                    frecuencia AS probabilidad,
                    impacto,
                    nivel,
                    CASE frecuencia
                        WHEN 'RARA' THEN 20
                        WHEN 'IMPROBABLE' THEN 40
                        WHEN 'POSIBLE' THEN 60
                        WHEN 'PROBABLE' THEN 80
                        WHEN 'CASI_SEGURO' THEN 100
                        ELSE 100
                    END AS maximo_baja_probabilidad,
                    CASE impacto
                        WHEN 'INSIGNIFICANTE' THEN 20
                        WHEN 'MENOR' THEN 40
                        WHEN 'MODERADO' THEN 60
                        WHEN 'MAYOR' THEN 80
                        WHEN 'CATASTROFICO' THEN 100
                        ELSE 100
                    END AS maximo_baja_impacto
                FROM riesgo
                ORDER BY id_riesgo DESC
                """
            )
            return cursor.fetchall()

    def cargar_controles(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id_control,
                    c.id_riesgo,
                    c.nombre,
                    c.descripcion,
                    c.tipo,
                    c.estado,
                    c.fecha_creacion,
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
                    r.nombre AS riesgo_nombre
                FROM control c
                INNER JOIN riesgo r
                    ON r.id_riesgo = c.id_riesgo
                ORDER BY c.id_control DESC
                """
            )
            return cursor.fetchall()

    def cargar_controles_por_riesgo(db, id_riesgo):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id_control,
                    nombre,
                    descripcion,
                    tipo,
                    solidez_control,
                    mitigacion_probabilidad,
                    mitigacion_impacto
                FROM control
                WHERE id_riesgo = %s
                ORDER BY id_control DESC
                LIMIT 12
                """,
                (id_riesgo,),
            )
            return cursor.fetchall()

    @app.get("/controles")
    async def controles(request: Request):
        flash = request.session.pop("flash", None)
        db = conexion.conectar()
        controles = []
        riesgos = []

        if db != "":
            riesgos = cargar_riesgos(db)
            controles = cargar_controles(db)
            db.close()

        return templates.TemplateResponse(
            name="controles.html",
            request=request,
            context={
                "flash": flash,
                "controles": controles,
                "riesgos": riesgos,
            },
        )

    @app.post("/control/recomendar")
    async def recomendar_control(request: Request):
        try:
            datos = await request.json()
        except Exception:
            return JSONResponse({"detail": "La solicitud no tiene un formato valido."}, status_code=400)

        nombre = (datos.get("nombre") or "").strip()
        descripcion = (datos.get("descripcion") or "").strip()
        nombres_excluidos = [
            texto_corto(nombre_excluido, 120).strip().lower()
            for nombre_excluido in (datos.get("nombres_excluidos") or [])
            if str(nombre_excluido or "").strip()
        ][:20]
        riesgo = datos.get("riesgo") or {}

        if not riesgo.get("id_riesgo"):
            return JSONResponse({"detail": "Seleccione el riesgo asociado antes de usar IA."}, status_code=400)

        controles_existentes = []
        db = conexion.conectar()
        if db != "":
            try:
                controles_existentes = cargar_controles_por_riesgo(db, riesgo.get("id_riesgo"))
            finally:
                db.close()

        configuraciones_ia = cargar_configuraciones_ia()
        if not configuraciones_ia:
            return JSONResponse(
                {"detail": "Configure GROQ_API_KEY, OPENAI_API_KEY o LISTA_APIS en el entorno o en el archivo .env."},
                status_code=503,
            )

        try:
            from openai import OpenAI
        except ImportError:
            return JSONResponse(
                {"detail": "Instale la dependencia openai con: pip install openai"},
                status_code=503,
            )

        maximo_probabilidad = porcentaje_formulario(riesgo.get("maximo_baja_probabilidad"), 100)
        maximo_impacto = porcentaje_formulario(riesgo.get("maximo_baja_impacto"), 100)
        entrada = {
            "control": {
                "nombre": texto_corto(nombre, 120),
                "descripcion_actual": texto_corto(descripcion, 260),
            },
            "nombres_sugeridos_en_esta_sesion": nombres_excluidos,
            "controles_existentes_del_riesgo": [
                {
                    "id_control": control.get("id_control"),
                    "nombre": texto_corto(control.get("nombre"), 120),
                    "descripcion": texto_corto(control.get("descripcion"), 220),
                    "tipo": control.get("tipo"),
                    "solidez_control": control.get("solidez_control"),
                    "mitigacion_probabilidad": control.get("mitigacion_probabilidad"),
                    "mitigacion_impacto": control.get("mitigacion_impacto"),
                }
                for control in controles_existentes
            ],
            "riesgo_asociado": {
                "id_riesgo": riesgo.get("id_riesgo"),
                "nombre": texto_corto(riesgo.get("nombre"), 120),
                "descripcion": texto_corto(riesgo.get("descripcion"), 260),
                "probabilidad": riesgo.get("probabilidad"),
                "impacto": riesgo.get("impacto"),
                "nivel": riesgo.get("nivel"),
                "maximo_baja_probabilidad": maximo_probabilidad,
                "maximo_baja_impacto": maximo_impacto,
            },
            "valores_validos": {
                "tipo": sorted(tipos_control),
                "solidez_control": sorted(solidez_opciones),
            },
            "criterios": [
                "Cada solicitud es independiente y sin memoria.",
                "Usa solo el control, riesgo_asociado y controles_existentes_del_riesgo recibidos.",
                "No inventes procesos, responsables ni datos externos.",
                "Si control.nombre esta vacio, crea un nombre nuevo de control adecuado para el riesgo.",
                "El nombre nuevo no debe repetir ni ser casi igual a ningun nombre de controles_existentes_del_riesgo.",
                "El nombre nuevo no debe repetir ni ser casi igual a ningun nombre de nombres_sugeridos_en_esta_sesion.",
                "Usa controles_existentes_del_riesgo solo como referencia para evitar duplicados y complementar cobertura.",
                "Si control.nombre tiene valor, conserva ese nombre y no lo reemplaces.",
                "Completa descripcion, tipo, solidez_control, mitigacion_probabilidad, mitigacion_impacto y explicacion.",
                "tipo y solidez_control deben estar en valores_validos.",
                "mitigacion_probabilidad no debe superar maximo_baja_probabilidad.",
                "mitigacion_impacto no debe superar maximo_baja_impacto.",
                "La explicacion debe decir por que el control mitiga ese riesgo.",
            ],
        }

        recomendacion = None
        errores_ia = []
        for config_ia in configuraciones_ia:
            try:
                client = OpenAI(api_key=config_ia["api_key"], base_url=config_ia["base_url"])
                respuesta = client.responses.create(
                    model=config_ia["model"],
                    instructions=(
                        "Eres especialista en controles internos y gestion de riesgos para MAGERISK. "
                        "Ayudas a completar un formulario de control usando el riesgo asociado como contexto. "
                        "Si falta nombre, propone un control nuevo y diferente a los controles existentes del riesgo. "
                        "Tambien debe ser diferente a los nombres ya sugeridos en esta misma sesion. "
                        "Si el usuario envio un nombre, mantenlo y completa el resto de campos acorde a ese nombre. "
                        "Responde solo JSON valido con: nombre, descripcion, tipo, solidez_control, "
                        "mitigacion_probabilidad, mitigacion_impacto, explicacion. "
                        "No uses memoria ni contexto de solicitudes anteriores."
                    ),
                    input=json.dumps(entrada, ensure_ascii=False),
                    text={"format": {"type": "json_object"}},
                )
                recomendacion = json.loads(respuesta.output_text)
                break
            except json.JSONDecodeError as error:
                errores_ia.append(detalle_error_ia(error, config_ia))
            except Exception as error:
                errores_ia.append(detalle_error_ia(error, config_ia))

        if recomendacion is None:
            return JSONResponse(
                {"detail": "No se pudo recomendar con ninguna API disponible. " + " | ".join(errores_ia[-3:])},
                status_code=502,
            )

        tipo = str(recomendacion.get("tipo") or "").strip()
        solidez_control = str(recomendacion.get("solidez_control") or "").strip()
        if tipo not in tipos_control:
            tipo = "Preventivo"
        if solidez_control not in solidez_opciones:
            solidez_control = "Media"

        nombre_sugerido = nombre
        if not nombre:
            nombres_existentes = {
                str(control.get("nombre") or "").strip().lower()
                for control in controles_existentes
                if str(control.get("nombre") or "").strip()
            }
            nombres_bloqueados = nombres_existentes | set(nombres_excluidos)
            nombre_ia = str(recomendacion.get("nombre") or "").strip()
            nombre_sugerido = nombre_ia
            if nombre_sugerido.lower() in nombres_bloqueados:
                base = f"Control complementario para {texto_corto(riesgo.get('nombre'), 80)}".strip()
                nombre_sugerido = base
                contador = 2
                while nombre_sugerido.lower() in nombres_bloqueados:
                    nombre_sugerido = f"{base} {contador}"
                    contador += 1
            if not nombre_sugerido:
                nombre_sugerido = f"Control preventivo para {texto_corto(riesgo.get('nombre'), 80)}".strip()

        mitigacion_probabilidad = min(
            porcentaje_formulario(recomendacion.get("mitigacion_probabilidad"), 0),
            maximo_probabilidad,
        )
        mitigacion_impacto = min(
            porcentaje_formulario(recomendacion.get("mitigacion_impacto"), 0),
            maximo_impacto,
        )

        return JSONResponse(
            content=jsonable_encoder({
                "nombre": texto_corto(nombre_sugerido, 120),
                "descripcion": texto_corto(recomendacion.get("descripcion"), 500),
                "tipo": tipo,
                "solidez_control": solidez_control,
                "mitigacion_probabilidad": mitigacion_probabilidad,
                "mitigacion_impacto": mitigacion_impacto,
                "explicacion": texto_corto(recomendacion.get("explicacion"), 700),
            })
        )

    @app.post("/crear_control")
    async def crear_control(request: Request):
        datos = await request.form()
        nombre = datos.get("nombre", "").strip()
        descripcion = datos.get("descripcion", "").strip()
        tipo = datos.get("tipo", "").strip()
        solidez_control = datos.get("solidez_control", "Media").strip()
        mitigacion_probabilidad = datos.get("mitigacion_probabilidad", "0").strip()
        mitigacion_impacto = datos.get("mitigacion_impacto", "0").strip()
        id_riesgo = datos.get("id_riesgo", "").strip()

        response = RedirectResponse("/controles", status_code=303)

        if not nombre or not tipo or not id_riesgo or not solidez_control:
            set_flash(request, "warning", "Complete los campos obligatorios.")
            return response

        if tipo not in tipos_control or solidez_control not in solidez_opciones:
            set_flash(request, "warning", "Seleccione valores válidos para el control.")
            return response

        mitigacion_probabilidad = porcentaje_formulario(mitigacion_probabilidad, 0)
        mitigacion_impacto = porcentaje_formulario(mitigacion_impacto, 0)

        db = conexion.conectar()
        if db == "":
            set_flash(request, "danger", "No se pudo conectar con la base de datos.")
            return response

        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO control (
                    nombre,
                    descripcion,
                    tipo,
                    solidez_control,
                    mitigacion_probabilidad,
                    mitigacion_impacto,
                    id_riesgo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    nombre,
                    descripcion or None,
                    tipo,
                    solidez_control,
                    mitigacion_probabilidad,
                    mitigacion_impacto,
                    id_riesgo,
                ),
            )
            db.commit()

        db.close()
        set_flash(request, "success", "Control registrado correctamente.")
        return response

    @app.post("/control/{id_control}/eliminar")
    async def eliminar_control(id_control: int, request: Request):
        response = RedirectResponse("/controles", status_code=303)
        db = conexion.conectar()

        if db == "":
            set_flash(request, "danger", "No se pudo conectar con la base de datos.")
            return response

        with db.cursor() as cursor:
            cursor.execute(
                "DELETE FROM control WHERE id_control = %s",
                (id_control,),
            )
            db.commit()

        db.close()
        set_flash(request, "success", "Control eliminado correctamente.")
        return response

    @app.post('/control/{id_control}/editar')
    async def editar_control(id_control: int, request: Request):
        datos = await request.form()
        nombre = datos.get('nombre', '').strip()
        descripcion = datos.get('descripcion', '').strip()
        tipo = datos.get('tipo', '').strip()
        solidez_control = datos.get('solidez_control', 'Media').strip()
        mitigacion_probabilidad = datos.get('mitigacion_probabilidad', '0').strip()
        mitigacion_impacto = datos.get('mitigacion_impacto', '0').strip()
        id_riesgo = datos.get('id_riesgo', '').strip()

        response = RedirectResponse('/controles', status_code=303)

        if not nombre or not tipo or not id_riesgo or not solidez_control:
            set_flash(request, 'warning', 'Complete los campos obligatorios.')
            return response

        if tipo not in tipos_control or solidez_control not in solidez_opciones:
            set_flash(request, 'warning', 'Seleccione valores válidos para el control.')
            return response

        mitigacion_probabilidad = porcentaje_formulario(mitigacion_probabilidad, 0)
        mitigacion_impacto = porcentaje_formulario(mitigacion_impacto, 0)

        db = conexion.conectar()
        if db == '':
            set_flash(request, 'danger', 'No se pudo conectar con la base de datos.')
            return response

        with db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE control
                SET nombre=%s,
                    descripcion=%s,
                    tipo=%s,
                    solidez_control=%s,
                    mitigacion_probabilidad=%s,
                    mitigacion_impacto=%s,
                    id_riesgo=%s
                WHERE id_control=%s
                """,
                (
                    nombre,
                    descripcion or None,
                    tipo,
                    solidez_control,
                    mitigacion_probabilidad,
                    mitigacion_impacto,
                    id_riesgo,
                    id_control,
                ),
            )
            db.commit()

        db.close()
        set_flash(request, 'success', 'Control actualizado correctamente.')
        return response
