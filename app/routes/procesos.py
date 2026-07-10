import json
import os
from pathlib import Path

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
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

    def cargar_grupos(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT id_grupo, nombre
                FROM grupo
                ORDER BY id_grupo ASC
                """
            )
            return cursor.fetchall()

    def asegurar_tablas_integrantes(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS rol (
                    id_rol INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(50) NOT NULL UNIQUE,
                    descripcion VARCHAR(255)
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS usuario_grupo (
                    id_usuario_grupo INT AUTO_INCREMENT PRIMARY KEY,
                    id_usuario INT NOT NULL,
                    id_grupo INT NOT NULL,
                    id_rol INT NOT NULL,
                    fecha_ingreso DATE DEFAULT (CURRENT_DATE),
                    estado ENUM('Activo','Inactivo') NOT NULL DEFAULT 'Activo',
                    CONSTRAINT fk_usuario_grupo_usuario
                        FOREIGN KEY (id_usuario)
                        REFERENCES usuario(id),
                    CONSTRAINT fk_usuario_grupo_grupo
                        FOREIGN KEY (id_grupo)
                        REFERENCES grupo(id_grupo),
                    CONSTRAINT fk_usuario_grupo_rol
                        FOREIGN KEY (id_rol)
                        REFERENCES rol(id_rol),
                    CONSTRAINT uq_usuario_grupo UNIQUE (id_usuario, id_grupo)
                )
                """
            )

            cursor.execute("SELECT COUNT(*) AS total FROM rol")
            total_roles = cursor.fetchone()["total"]
            if total_roles == 0:
                cursor.execute(
                    """
                    INSERT INTO rol (nombre, descripcion) VALUES
                    ('Administrador', 'Administra el grupo y sus integrantes'),
                    ('Líder', 'Responsable del grupo'),
                    ('Miembro', 'Participa en las actividades del grupo'),
                    ('Observador', 'Solo tiene permisos de consulta')
                    """
                )

            db.commit()

    def cargar_roles(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT id_rol, nombre, descripcion
                FROM rol
                ORDER BY id_rol ASC
                """
            )
            return cursor.fetchall()

    def cargar_integrantes_grupo(db, id_grupo):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ug.id_usuario_grupo,
                    u.id AS id_usuario,
                    u.nombres_completo,
                    u.correo,
                    r.id_rol,
                    r.nombre AS rol_nombre,
                    ug.fecha_ingreso,
                    ug.estado
                FROM usuario_grupo ug
                INNER JOIN usuario u ON u.id = ug.id_usuario
                INNER JOIN rol r ON r.id_rol = ug.id_rol
                WHERE ug.id_grupo = %s
                  AND ug.estado = 'Activo'
                ORDER BY u.nombres_completo ASC
                """,
                (id_grupo,)
            )
            return cursor.fetchall()

    def cargar_procesos(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.id_proceso,
                    p.nombre,
                    p.descripcion,
                    p.fecha_creacion,
                    g.id_grupo,
                    g.nombre AS grupo_nombre
                FROM proceso p
                INNER JOIN grupo g ON g.id_grupo = p.id_grupo
                ORDER BY p.id_proceso DESC
                """
            )
            return cursor.fetchall()

    def cargar_proceso_por_id(db, id_proceso):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.id_proceso,
                    p.nombre,
                    p.descripcion,
                    g.nombre AS grupo_nombre
                FROM proceso p
                INNER JOIN grupo g ON g.id_grupo = p.id_grupo
                WHERE p.id_proceso = %s
                """,
                (id_proceso,),
            )
            return cursor.fetchone()

    def cargar_riesgos_para_asistente(db, id_proceso):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    r.id_riesgo,
                    r.nombre,
                    r.descripcion,
                    r.impacto,
                    r.frecuencia AS probabilidad,
                    r.nivel,
                    CASE WHEN rp.id_proceso IS NULL THEN 0 ELSE 1 END AS asociado
                FROM riesgo r
                LEFT JOIN riesgo_proceso rp
                    ON rp.id_riesgo = r.id_riesgo
                   AND rp.id_proceso = %s
                ORDER BY asociado DESC, r.id_riesgo DESC
                """,
                (id_proceso,),
            )
            riesgos = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    c.id_control,
                    c.id_riesgo,
                    c.nombre,
                    c.descripcion,
                    c.tipo,
                    c.estado,
                    c.solidez_control,
                    c.mitigacion_probabilidad,
                    c.mitigacion_impacto
                FROM control c
                ORDER BY c.id_control DESC
                """
            )
            controles_por_riesgo = {}
            for control in cursor.fetchall():
                if not control.get("id_control") or not (control.get("nombre") or "").strip():
                    continue
                controles_por_riesgo.setdefault(control["id_riesgo"], []).append(control)

        for riesgo in riesgos:
            riesgo["asociado"] = bool(riesgo.get("asociado"))
            riesgo["controles"] = controles_por_riesgo.get(riesgo["id_riesgo"], [])

        return riesgos

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

    def texto_corto(valor, limite=120):
        texto = str(valor or "").strip()
        if len(texto) <= limite:
            return texto
        return texto[:limite].rstrip() + "..."

    def esquema_recomendacion_riesgos():
        control_schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "nombre": {"type": "string"},
                "descripcion": {"type": "string"},
                "tipo": {
                    "type": "string",
                    "enum": ["Preventivo", "Detectivo", "Correctivo"],
                },
                "solidez_control": {
                    "type": "string",
                    "enum": ["Muy baja", "Baja", "Media", "Alta", "Muy alta"],
                },
                "mitigacion_probabilidad": {"type": "number"},
                "mitigacion_impacto": {"type": "number"},
            },
            "required": [
                "nombre",
                "descripcion",
                "tipo",
                "solidez_control",
                "mitigacion_probabilidad",
                "mitigacion_impacto",
            ],
        }

        riesgo_schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "nombre": {"type": "string"},
                "descripcion": {"type": "string"},
                "causa": {"type": "string"},
                "consecuencia": {"type": "string"},
                "probabilidad": {
                    "type": "string",
                    "enum": ["RARA", "IMPROBABLE", "POSIBLE", "PROBABLE", "CASI_SEGURO"],
                },
                "impacto": {
                    "type": "string",
                    "enum": ["INSIGNIFICANTE", "MENOR", "MODERADO", "MAYOR", "CATASTROFICO"],
                },
                "controles": {
                    "type": "array",
                    "items": control_schema,
                },
            },
            "required": [
                "nombre",
                "descripcion",
                "causa",
                "consecuencia",
                "probabilidad",
                "impacto",
                "controles",
            ],
        }

        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "resumen": {"type": "string"},
                "riesgos": {
                    "type": "array",
                    "items": riesgo_schema,
                },
            },
            "required": ["resumen", "riesgos"],
        }

    def esquema_asistente_nuevo_proceso():
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "resumen": {"type": "string"},
                "descripcion_sugerida": {"type": "string"},
                "id_grupo_sugerido": {"type": "number"},
                "grupo_motivo": {"type": "string"},
                "riesgos_aplicables": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "id_riesgo": {"type": "number"},
                            "motivo": {"type": "string"},
                            "prioridad": {
                                "type": "string",
                                "enum": ["Alta", "Media", "Baja"],
                            },
                        },
                        "required": ["id_riesgo", "motivo", "prioridad"],
                    },
                },
            },
            "required": ["resumen", "descripcion_sugerida", "id_grupo_sugerido", "grupo_motivo", "riesgos_aplicables"],
        }

    def asegurar_tabla_proceso(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS proceso (
                    id_proceso INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(150) NOT NULL,
                    descripcion VARCHAR(255),
                    id_grupo INT NOT NULL,
                    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_proceso_grupo
                        FOREIGN KEY (id_grupo)
                        REFERENCES grupo(id_grupo)
                )
                """
            )
            db.commit()

    def sembrar_procesos_si_vacio(db):
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM proceso")
            total = cursor.fetchone()["total"]
            if total > 0:
                return

            grupos = cargar_grupos(db)
            if not grupos:
                return

            semillas = [
                ("Validacion Funcional", "Casos de prueba y validacion de entregables.", 6),
                ("Indicadores y Reportes", "Construccion de tableros e indicadores para la gestion.", 5),
                ("Analisis de Seguridad", "Revision de riesgos, amenazas y controles asociados.", 3),
                ("Seguimiento Ejecutivo", "Control del avance general y coordinacion de hitos.", 1),
                ("Tableros BI", "Visualizacion ejecutiva de indicadores para el seguimiento.", 5),
            ]

            semillas_validas = [item for item in semillas if item[2] is not None]

            for indice, (nombre, descripcion, id_grupo) in enumerate(semillas_validas, start=1):
                cursor.execute(
                    """
                    INSERT INTO proceso (nombre, descripcion, id_grupo)
                    VALUES (%s, %s, %s)
                    """,
                    (nombre, descripcion, id_grupo)
                )

            db.commit()

    @app.get("/procesos")
    async def procesos(request: Request):
        flash = request.session.pop("flash", None)
        db = conexion.conectar()
        procesos = []
        grupos = []

        if db != "":
            asegurar_tabla_proceso(db)
            grupos = cargar_grupos(db)
            procesos = cargar_procesos(db)
            db.close()

        return templates.TemplateResponse(
            name="procesos.html",
            request=request,
            context={
                "flash": flash,
                "procesos": procesos,
                "grupos": grupos,
            },
        )

    @app.post("/crear_proceso")
    async def crear_proceso(request: Request):
        datos = await request.form()
        nombre = datos.get("nombre", "").strip()
        descripcion = datos.get("descripcion", "").strip()
        id_grupo = datos.get("id_grupo", "").strip()
        riesgos_asociados = []
        for valor in datos.getlist("riesgos_asociados"):
            try:
                id_riesgo = int(valor)
            except (TypeError, ValueError):
                continue
            if id_riesgo > 0 and id_riesgo not in riesgos_asociados:
                riesgos_asociados.append(id_riesgo)

        response = RedirectResponse("/procesos", status_code=303)

        if not nombre or not id_grupo:
            set_flash(request, "warning", "Complete los campos obligatorios.")
            return response

        db = conexion.conectar()
        if db == "":
            set_flash(request, "danger", "No se pudo conectar con la base de datos.")
            return response

        with db.cursor() as cursor:
            asegurar_tabla_proceso(db)

            cursor.execute(
                """
                INSERT INTO proceso (nombre, descripcion, id_grupo)
                VALUES (%s, %s, %s)
                """,
                (nombre, descripcion or None, id_grupo),
            )
            id_proceso = cursor.lastrowid

            riesgos_validos = []
            if riesgos_asociados:
                placeholders = ", ".join(["%s"] * len(riesgos_asociados))
                cursor.execute(
                    f"""
                    SELECT id_riesgo
                    FROM riesgo
                    WHERE id_riesgo IN ({placeholders})
                    """,
                    tuple(riesgos_asociados),
                )
                riesgos_validos = [fila["id_riesgo"] for fila in cursor.fetchall()]

            for id_riesgo in riesgos_validos:
                cursor.execute(
                    """
                    INSERT INTO riesgo_proceso (id_riesgo, id_proceso)
                    VALUES (%s, %s)
                    """,
                    (id_riesgo, id_proceso),
                )
            db.commit()

        db.close()
        if riesgos_asociados:
            set_flash(request, "success", f"Proceso creado correctamente con {len(riesgos_validos)} riesgo(s) asociado(s).")
        else:
            set_flash(request, "success", "Proceso creado correctamente.")
        return response

    @app.post("/procesos/recomendar_riesgos_nuevo")
    async def recomendar_riesgos_nuevo_proceso(request: Request):
        datos = await request.json()
        nombre = (datos.get("nombre") or "").strip()
        descripcion = (datos.get("descripcion") or "").strip()
        grupo_nombre = (datos.get("grupo_nombre") or "").strip()
        grupos_disponibles = datos.get("grupos_disponibles") or []
        try:
            id_proceso_contexto = int(datos.get("id_proceso") or 0)
        except (TypeError, ValueError):
            id_proceso_contexto = 0

        if not nombre:
            return JSONResponse({"detail": "Ingrese el nombre del proceso antes de usar IA."}, status_code=400)

        db = conexion.conectar()
        if db == "":
            return JSONResponse({"detail": "No se pudo conectar con la base de datos."}, status_code=500)

        riesgos_sistema = cargar_riesgos_para_asistente(db, id_proceso_contexto or None)
        riesgos_candidatos = [
            riesgo
            for riesgo in riesgos_sistema
            if not (id_proceso_contexto and riesgo.get("asociado"))
        ]
        db.close()

        if not riesgos_candidatos:
            return JSONResponse(
                content=jsonable_encoder({
                    "proceso_borrador": {
                        "nombre": nombre,
                        "descripcion": descripcion,
                        "grupo_nombre": grupo_nombre,
                    },
                    "riesgos_sistema": riesgos_sistema,
                    "recomendacion": {
                        "resumen": "No hay nuevos riesgos pendientes para recomendar.",
                        "descripcion_sugerida": descripcion,
                        "id_grupo_sugerido": 0,
                        "grupo_motivo": "",
                        "riesgos_aplicables": [],
                    },
                })
            )

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

        riesgos_contexto = []
        for riesgo in riesgos_candidatos[:35]:
            riesgos_contexto.append({
                "id_riesgo": riesgo.get("id_riesgo"),
                "nombre": texto_corto(riesgo.get("nombre"), 80),
                "descripcion": texto_corto(riesgo.get("descripcion"), 120),
                "probabilidad": riesgo.get("probabilidad"),
                "impacto": riesgo.get("impacto"),
                "nivel": riesgo.get("nivel"),
            })

        instrucciones = (
            "Eres especialista en gestion de riesgos para MAGERISK. "
            "Analiza un proceso de MAGERISK. "
            "Cada solicitud es independiente y sin memoria: usa solo el JSON actual recibido como entrada. "
            "Ignora cualquier nombre, descripcion, proyecto o contexto de solicitudes anteriores aunque parezca relacionado. "
            "No agregues contexto que no exista en el nombre o descripcion del proceso. "
            "No asumas horarios, turnos, responsables, documentos, actas, objetivos ni validaciones si no fueron mencionados. "
            "Completa una descripcion profesional y sugiere el grupo responsable mas adecuado usando solo id_grupo de la lista recibida. "
            "Debes elegir riesgos existentes que aplican usando solo id_riesgo de la lista recibida. "
            "No recibiras controles. No recomiendes controles. El sistema los obtendra de la base de datos despues. "
            "No inventes riesgos nuevos. "
            "Si ningun riesgo existente se relaciona claramente, devuelve riesgos_aplicables como lista vacia y explica que no se recomienda asociar riesgos por ahora. "
            "Devuelve solo JSON valido con resumen, descripcion_sugerida, id_grupo_sugerido, grupo_motivo y riesgos_aplicables."
        )
        entrada = json.dumps({
            "proceso_nuevo": {
                "nombre": nombre,
                "descripcion": descripcion or "Sin descripcion escrita todavia",
                "grupo_responsable": grupo_nombre or "No seleccionado",
            },
            "grupos_disponibles": grupos_disponibles,
            "riesgos_existentes": riesgos_contexto,
            "criterios": [
                "Selecciona solo los riesgos mas importantes, maximo 6.",
                "Selecciona cero riesgos si no hay una relacion clara.",
                "Prefiere no asociar nada antes que forzar una coincidencia debil.",
                "No listes todos los riesgos.",
                "Si recibes riesgos ya asociados al proceso, no los recomiendes otra vez.",
                "No inventes id_riesgo ni id_grupo.",
                "No menciones controles.",
                "No reutilices nombres de procesos anteriores ni proyectos previos.",
                "Si un dato no aparece en proceso_nuevo, no lo uses ni lo infieras desde conversaciones anteriores.",
                "El campo motivo debe explicar con precision por que ese riesgo aplica al proceso.",
                "La descripcion_sugerida debe describir solo lo inferible del nombre y descripcion dados, sin inventar detalles operativos.",
                "Si ningun grupo aplica claramente, usa id_grupo_sugerido 0.",
            ],
        }, ensure_ascii=False)

        recomendacion = None
        errores_ia = []
        for config_ia in configuraciones_ia:
            try:
                client = OpenAI(api_key=config_ia["api_key"], base_url=config_ia["base_url"])
                try:
                    respuesta = client.responses.create(
                        model=config_ia["model"],
                        instructions=instrucciones,
                        input=entrada,
                        text={
                            "format": {
                                "type": "json_schema",
                                "name": "asistente_nuevo_proceso",
                                "schema": esquema_asistente_nuevo_proceso(),
                                "strict": True,
                            }
                        },
                    )
                except Exception as error_schema:
                    mensaje_schema = str(error_schema)
                    if config_ia["proveedor"] != "groq" or "json_validate_failed" not in mensaje_schema:
                        raise

                    respuesta = client.responses.create(
                        model=config_ia["model"],
                        instructions=instrucciones,
                        input=entrada,
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

        ids_validos = {
            int(riesgo["id_riesgo"])
            for riesgo in riesgos_candidatos
            if riesgo.get("id_riesgo") is not None
        }
        aplicables_filtrados = []
        ids_agregados = set()
        for item in recomendacion.get("riesgos_aplicables", []):
            try:
                id_riesgo = int(item.get("id_riesgo"))
            except (TypeError, ValueError):
                continue
            if id_riesgo in ids_validos and id_riesgo not in ids_agregados:
                item["id_riesgo"] = id_riesgo
                aplicables_filtrados.append(item)
                ids_agregados.add(id_riesgo)
        recomendacion["riesgos_aplicables"] = aplicables_filtrados[:6]
        ids_grupos_validos = {
            int(grupo.get("id_grupo"))
            for grupo in grupos_disponibles
            if grupo.get("id_grupo") is not None
        }
        try:
            id_grupo_sugerido = int(recomendacion.get("id_grupo_sugerido") or 0)
        except (TypeError, ValueError):
            id_grupo_sugerido = 0
        if id_grupo_sugerido not in ids_grupos_validos:
            id_grupo_sugerido = 0
        recomendacion["id_grupo_sugerido"] = id_grupo_sugerido

        return JSONResponse(
            content=jsonable_encoder({
                "proceso_borrador": {
                    "nombre": nombre,
                    "descripcion": descripcion,
                    "grupo_nombre": grupo_nombre,
                },
                "riesgos_sistema": riesgos_sistema,
                "recomendacion": recomendacion,
            })
        )

    @app.get("/procesos/{id_proceso}/riesgos")
    async def riesgos_asociados_proceso(id_proceso: int):
        db = conexion.conectar()
        if db == "":
            return JSONResponse({"detail": "No se pudo conectar con la base de datos."}, status_code=500)

        proceso = cargar_proceso_por_id(db, id_proceso)
        if proceso is None:
            db.close()
            return JSONResponse({"detail": "El proceso no existe."}, status_code=404)

        riesgos = [
            riesgo
            for riesgo in cargar_riesgos_para_asistente(db, id_proceso)
            if riesgo.get("asociado")
        ]
        db.close()

        return JSONResponse(
            content=jsonable_encoder({
                "id_proceso": id_proceso,
                "riesgos": riesgos,
            })
        )

    @app.get("/procesos/{id_proceso}/riesgos_disponibles")
    async def riesgos_disponibles_proceso(id_proceso: int):
        db = conexion.conectar()
        if db == "":
            return JSONResponse({"detail": "No se pudo conectar con la base de datos."}, status_code=500)

        proceso = cargar_proceso_por_id(db, id_proceso)
        riesgos = cargar_riesgos_para_asistente(db, id_proceso) if proceso else []
        db.close()
        if proceso is None:
            return JSONResponse({"detail": "El proceso no existe."}, status_code=404)

        return JSONResponse(content=jsonable_encoder({
            "proceso": proceso,
            "riesgos": riesgos,
        }))

    @app.post("/procesos/{id_proceso}/agregar_riesgos")
    async def agregar_riesgos_proceso(id_proceso: int, request: Request):
        try:
            datos = await request.json()
        except Exception:
            return JSONResponse({"detail": "La solicitud no tiene un formato valido."}, status_code=400)

        valores = datos.get("riesgos", []) if isinstance(datos, dict) else []
        ids_riesgos = []
        for valor in valores:
            try:
                id_riesgo = int(valor)
            except (TypeError, ValueError):
                continue
            if id_riesgo > 0 and id_riesgo not in ids_riesgos:
                ids_riesgos.append(id_riesgo)

        db = conexion.conectar()
        if db == "":
            return JSONResponse({"detail": "No se pudo conectar con la base de datos."}, status_code=500)

        try:
            with db.cursor() as cursor:
                cursor.execute("SELECT id_proceso FROM proceso WHERE id_proceso=%s", (id_proceso,))
                if cursor.fetchone() is None:
                    db.close()
                    return JSONResponse({"detail": "El proceso no existe."}, status_code=404)

                validos = []
                if ids_riesgos:
                    placeholders = ", ".join(["%s"] * len(ids_riesgos))
                    cursor.execute(
                        f"SELECT id_riesgo FROM riesgo WHERE id_riesgo IN ({placeholders})",
                        tuple(ids_riesgos),
                    )
                    validos = [int(row["id_riesgo"]) for row in cursor.fetchall()]

                seleccionados = set(validos)
                cursor.execute(
                    "SELECT id_riesgo FROM riesgo_proceso WHERE id_proceso=%s",
                    (id_proceso,),
                )
                actuales = {int(row["id_riesgo"]) for row in cursor.fetchall()}

                para_agregar = sorted(seleccionados - actuales)
                para_quitar = sorted(actuales - seleccionados)

                for id_riesgo in para_agregar:
                    cursor.execute(
                        "INSERT IGNORE INTO riesgo_proceso (id_riesgo, id_proceso) VALUES (%s, %s)",
                        (id_riesgo, id_proceso),
                    )

                if para_quitar:
                    placeholders = ", ".join(["%s"] * len(para_quitar))
                    cursor.execute(
                        f"""
                        DELETE FROM riesgo_proceso
                        WHERE id_proceso=%s
                          AND id_riesgo IN ({placeholders})
                        """,
                        (id_proceso, *para_quitar),
                    )

                db.commit()
        except Exception:
            db.rollback()
            db.close()
            return JSONResponse({"detail": "No se pudieron guardar las asociaciones de riesgos."}, status_code=500)

        db.close()

        return JSONResponse({
            "ok": True,
            "seleccionados": len(seleccionados),
            "agregados": len(para_agregar),
            "quitados": len(para_quitar),
        })

    @app.post('/procesos/{id_proceso}/editar')
    async def editar_proceso(id_proceso: int, request: Request):
        datos = await request.form()
        nombre = datos.get('nombre', '').strip()
        descripcion = datos.get('descripcion', '').strip()
        id_grupo = datos.get('id_grupo', '').strip()

        response = RedirectResponse('/procesos', status_code=303)

        if not nombre or not id_grupo:
            set_flash(request, 'warning', 'Complete los campos obligatorios.')
            return response

        db = conexion.conectar()
        if db == '':
            set_flash(request, 'danger', 'No se pudo conectar con la base de datos.')
            return response

        with db.cursor() as cursor:
            cursor.execute(
                'UPDATE proceso SET nombre=%s, descripcion=%s, id_grupo=%s WHERE id_proceso=%s',
                (nombre, descripcion or None, id_grupo, id_proceso),
            )
            db.commit()

        db.close()
        set_flash(request, 'success', 'Proceso actualizado correctamente.')
        return response

    @app.post("/procesos/{id_proceso}/eliminar")
    async def eliminar_proceso(id_proceso: int, request: Request):
        response = RedirectResponse("/procesos", status_code=303)
        db = conexion.conectar()

        if db == "":
            set_flash(request, "danger", "No se pudo conectar con la base de datos.")
            return response

        with db.cursor() as cursor:
            cursor.execute(
                "DELETE FROM proceso WHERE id_proceso=%s",
                (id_proceso,),
            )
            db.commit()

        db.close()
        set_flash(request, "success", "Proceso eliminado correctamente.")
        return response

    @app.post("/procesos/{id_proceso}/recomendar_riesgos")
    async def recomendar_riesgos_proceso(id_proceso: int):
        db = conexion.conectar()
        if db == "":
            return JSONResponse(
                {"detail": "No se pudo conectar con la base de datos."},
                status_code=500,
            )

        proceso = cargar_proceso_por_id(db, id_proceso)
        riesgos_sistema = cargar_riesgos_para_asistente(db, id_proceso)
        db.close()

        if proceso is None:
            return JSONResponse({"detail": "El proceso no existe."}, status_code=404)

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

        descripcion = proceso.get("descripcion") or "Sin descripción registrada"
        nombres_riesgos_existentes = [
            riesgo.get("nombre", "")
            for riesgo in riesgos_sistema
            if riesgo.get("nombre")
        ][:30]
        nombres_controles_existentes = []
        for riesgo in riesgos_sistema:
            for control in riesgo.get("controles", []):
                if control.get("nombre"):
                    nombres_controles_existentes.append(control["nombre"])
        nombres_controles_existentes = nombres_controles_existentes[:40]

        instrucciones = (
            "Eres un especialista en gestion de riesgos operacionales. "
            "Recomienda riesgos y controles aplicables a un proceso. "
            "Usa lenguaje claro, concreto y util para un sistema llamado MAGERISK. "
            "No inventes datos legales ni financieros especificos. "
            "Devuelve solo JSON valido con esta estructura exacta: "
            "{resumen: string, riesgos: [{nombre, descripcion, causa, consecuencia, "
            "probabilidad, impacto, controles: [{nombre, descripcion, tipo, "
            "solidez_control, mitigacion_probabilidad, mitigacion_impacto}]}]}."
        )
        entrada = (
            f"Proceso: {proceso['nombre']}\n"
            f"Descripcion: {descripcion}\n"
            f"Grupo responsable: {proceso.get('grupo_nombre') or 'No especificado'}\n\n"
            f"Riesgos que ya existen en el sistema y no debes duplicar: {', '.join(nombres_riesgos_existentes) or 'ninguno'}.\n"
            f"Controles que ya existen en el sistema y no debes duplicar: {', '.join(nombres_controles_existentes) or 'ninguno'}.\n\n"
            "Genera de 3 a 5 riesgos principales. Para cada riesgo, agrega de 1 a 3 controles. "
            "Usa probabilidad en RARA, IMPROBABLE, POSIBLE, PROBABLE o CASI_SEGURO. "
            "Usa impacto en INSIGNIFICANTE, MENOR, MODERADO, MAYOR o CATASTROFICO. "
            "Usa tipo de control Preventivo, Detectivo o Correctivo. "
            "Si un riesgo o control ya existe, propone una alternativa diferente o mas especifica."
        )

        recomendaciones = None
        errores_ia = []
        for config_ia in configuraciones_ia:
            try:
                client = OpenAI(
                    api_key=config_ia["api_key"],
                    base_url=config_ia["base_url"],
                )
                try:
                    respuesta = client.responses.create(
                        model=config_ia["model"],
                        instructions=instrucciones,
                        input=entrada,
                        text={
                            "format": {
                                "type": "json_schema",
                                "name": "recomendacion_riesgos_proceso",
                                "schema": esquema_recomendacion_riesgos(),
                                "strict": True,
                            }
                        },
                    )
                except Exception as error_schema:
                    mensaje_schema = str(error_schema)
                    if config_ia["proveedor"] != "groq" or "json_validate_failed" not in mensaje_schema:
                        raise

                    respuesta = client.responses.create(
                        model=config_ia["model"],
                        instructions=instrucciones,
                        input=entrada,
                        text={"format": {"type": "json_object"}},
                    )

                recomendaciones = json.loads(respuesta.output_text)
                break
            except json.JSONDecodeError as error:
                errores_ia.append(detalle_error_ia(error, config_ia))
            except Exception as error:
                errores_ia.append(detalle_error_ia(error, config_ia))

        if recomendaciones is None:
            return JSONResponse(
                {"detail": "No se pudo recomendar con ninguna API disponible. " + " | ".join(errores_ia[-3:])},
                status_code=502,
            )

        return JSONResponse(
            content=jsonable_encoder({
                "proceso": proceso,
                "riesgos_sistema": riesgos_sistema,
                "recomendaciones": recomendaciones,
            })
        )

    @app.get("/grupos")
    async def grupos(request: Request):
        flash = request.session.pop("flash", None)
        db = conexion.conectar()
        grupos = []

        if db != "":
            asegurar_tablas_integrantes(db)
            with db.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        g.id_grupo,
                        g.nombre,
                        g.descripcion,
                        COUNT(ug.id_usuario_grupo) AS total_integrantes
                    FROM grupo g
                    LEFT JOIN usuario_grupo ug
                        ON ug.id_grupo = g.id_grupo
                       AND ug.estado = 'Activo'
                    GROUP BY
                        g.id_grupo,
                        g.nombre,
                        g.descripcion
                    ORDER BY g.id_grupo DESC
                    """
                )
                grupos = cursor.fetchall()
            db.close()

        return templates.TemplateResponse(
            name="grupos.html",
            request=request,
            context={
                "flash": flash,
                "grupos": grupos,
            },
        )

    @app.get("/roles/listar")
    def listar_roles():
        db = conexion.conectar()
        if db == "":
            return JSONResponse([])

        roles = []
        with db.cursor() as cursor:
            asegurar_tablas_integrantes(db)
            roles = cargar_roles(db)

        db.close()
        return JSONResponse(content=jsonable_encoder(roles))

    @app.get("/grupo/{id_grupo}/integrantes")
    def listar_integrantes_grupo(id_grupo: int):
        db = conexion.conectar()
        if db == "":
            return JSONResponse([])

        integrantes = []
        with db.cursor() as cursor:
            asegurar_tablas_integrantes(db)
            integrantes = cargar_integrantes_grupo(db, id_grupo)

        db.close()
        return JSONResponse(content=jsonable_encoder(integrantes))

    @app.post("/crear_grupo")
    async def crear_grupo(request: Request):
        datos = await request.form()
        nombre = datos.get("nombre", "").strip()
        descripcion = datos.get("descripcion", "").strip()

        response = RedirectResponse("/grupos", status_code=303)

        if not nombre:
            set_flash(request, "warning", "El nombre es obligatorio.")
            return response

        db = conexion.conectar()
        if db == "":
            set_flash(request, "danger", "No se pudo conectar con la base de datos.")
            return response

        with db.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS grupo (
                    id_grupo INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    descripcion VARCHAR(255) NULL,
                    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                INSERT INTO grupo (nombre, descripcion)
                VALUES (%s, %s)
                """,
                (nombre, descripcion or None),
            )
            db.commit()

        db.close()
        set_flash(request, "success", "Grupo creado correctamente.")
        return response

    @app.post('/grupo/{id_grupo}/editar')
    async def editar_grupo(id_grupo: int, request: Request):
        datos = await request.form()
        nombre = datos.get('nombre', '').strip()
        descripcion = datos.get('descripcion', '').strip()

        response = RedirectResponse('/grupos', status_code=303)

        if not nombre:
            set_flash(request, 'warning', 'El nombre es obligatorio.')
            return response

        db = conexion.conectar()
        if db == '':
            set_flash(request, 'danger', 'No se pudo conectar con la base de datos.')
            return response

        with db.cursor() as cursor:
            cursor.execute(
                'UPDATE grupo SET nombre=%s, descripcion=%s WHERE id_grupo=%s',
                (nombre, descripcion or None, id_grupo),
            )
            db.commit()

        db.close()
        set_flash(request, 'success', 'Grupo actualizado correctamente.')
        return response

    @app.post("/grupo/{id_grupo}/integrantes/asignar")
    async def asignar_integrante_grupo(id_grupo: int, request: Request):
        datos = await request.form()
        correo = datos.get("correo", "").strip()
        id_rol = datos.get("id_rol", "").strip()
        response = JSONResponse({"ok": True})

        if not correo or not id_rol:
            return JSONResponse({"detail": "Complete la persona y el rol."}, status_code=400)

        db = conexion.conectar()
        if db == "":
            return JSONResponse({"detail": "No se pudo conectar con la base de datos."}, status_code=500)

        with db.cursor() as cursor:
            asegurar_tablas_integrantes(db)

            cursor.execute(
                "SELECT id FROM usuario WHERE correo=%s",
                (correo,)
            )
            usuario = cursor.fetchone()
            if usuario is None:
                db.close()
                return JSONResponse({"detail": "La persona seleccionada no existe."}, status_code=404)

            cursor.execute(
                "SELECT id_rol FROM rol WHERE id_rol=%s",
                (id_rol,)
            )
            rol = cursor.fetchone()
            if rol is None:
                db.close()
                return JSONResponse({"detail": "El rol seleccionado no existe."}, status_code=404)

            cursor.execute(
                """
                SELECT id_usuario_grupo
                FROM usuario_grupo
                WHERE id_usuario=%s
                  AND id_grupo=%s
                """,
                (usuario["id"], id_grupo)
            )
            existente = cursor.fetchone()

            if existente:
                cursor.execute(
                    """
                    UPDATE usuario_grupo
                    SET id_rol=%s,
                        estado='Activo',
                        fecha_ingreso=CURRENT_DATE
                    WHERE id_usuario_grupo=%s
                    """,
                    (id_rol, existente["id_usuario_grupo"])
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO usuario_grupo (id_usuario, id_grupo, id_rol, estado)
                    VALUES (%s, %s, %s, 'Activo')
                    """,
                    (usuario["id"], id_grupo, id_rol)
                )

            db.commit()

        db.close()
        return response

    @app.post("/grupo/{id_grupo}/integrantes/{id_usuario_grupo}/quitar")
    def quitar_integrante_grupo(id_grupo: int, id_usuario_grupo: int):
        db = conexion.conectar()
        if db == "":
            return JSONResponse({"detail": "No se pudo conectar con la base de datos."}, status_code=500)

        with db.cursor() as cursor:
            asegurar_tablas_integrantes(db)

            cursor.execute(
                """
                UPDATE usuario_grupo
                SET estado='Inactivo'
                WHERE id_usuario_grupo=%s
                  AND id_grupo=%s
                """,
                (id_usuario_grupo, id_grupo)
            )
            db.commit()

        db.close()
        return JSONResponse({"ok": True})

    @app.post("/grupo/{id_grupo}/eliminar")
    async def eliminar_grupo(id_grupo: int, request: Request):
        response = RedirectResponse("/grupos", status_code=303)
        db = conexion.conectar()

        if db == "":
            set_flash(request, "danger", "No se pudo conectar con la base de datos.")
            return response

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM proceso WHERE id_grupo=%s",
                (id_grupo,),
            )
            asociados = cursor.fetchone()["total"]
            if asociados > 0:
                db.close()
                set_flash(request, "warning", "No se puede eliminar porque el grupo tiene procesos asociados.")
                return response

            cursor.execute(
                "DELETE FROM grupo WHERE id_grupo=%s",
                (id_grupo,),
            )
            db.commit()

        db.close()
        set_flash(request, "success", "Grupo eliminado correctamente.")
        return response
