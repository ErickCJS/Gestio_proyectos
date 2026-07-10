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
            "texto": texto
        }

    # ----------------------------------------
    # MATRIZ PIRANI
    # ----------------------------------------

    valores_impacto = {
        "INSIGNIFICANTE":1,
        "MENOR":2,
        "MODERADO":3,
        "MAYOR":4,
        "CATASTROFICO":5
    }

    valores_probabilidad = {
        "RARA":1,
        "IMPROBABLE":2,
        "POSIBLE":3,
        "PROBABLE":4,
        "CASI_SEGURO":5
    }


    def calcular_nivel(impacto, probabilidad):

        total = (
            valores_impacto[impacto] *
            valores_probabilidad[probabilidad]
        )
        if total == 1:
            return "MUY BAJO"
        elif total <= 4:
            return "BAJO"
        elif total <= 9:
            return "MEDIO"
        elif total <= 16:
            return "ALTO"
        return "EXTREMO"

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

    # ----------------------------------------
    # CONSULTAS
    # ----------------------------------------

    def cargar_riesgos(db):
        with db.cursor() as cursor:
            cursor.execute("""
            SELECT *
            FROM riesgo
            ORDER BY id_riesgo DESC
            """)
            return cursor.fetchall()

    def cargar_procesos(db):
        with db.cursor() as cursor:
            cursor.execute("""
            SELECT
                id_proceso,
                nombre
            FROM proceso
            ORDER BY nombre
            """)
            return cursor.fetchall()



    def cargar_procesos_riesgo(db,id_riesgo):
        with db.cursor() as cursor:
            cursor.execute("""
            SELECT
                p.id_proceso,
                p.nombre
            FROM riesgo_proceso rp
            INNER JOIN proceso p
                ON p.id_proceso=rp.id_proceso
            WHERE rp.id_riesgo=%s
            """,(id_riesgo,))
            return cursor.fetchall()

    # --------------------------------------------------
    # VISTA
    # --------------------------------------------------

    @app.get("/riesgo")
    async def riesgo(request:Request):
        flash=request.session.pop("flash",None)
        db=conexion.conectar()
        riesgos=[]
        procesos=[]
        mapa=[]
        if db!="":
            riesgos=cargar_riesgos(db)
            procesos=cargar_procesos(db)
            for riesgo in riesgos:
                riesgo["probabilidad"] = riesgo["frecuencia"]
                riesgo["procesos"]=cargar_procesos_riesgo(
                    db,
                    riesgo["id_riesgo"]
                )
            mapa=[0]*25
            for riesgo in riesgos:
                x=valores_probabilidad[riesgo["probabilidad"]]-1
                y=valores_impacto[riesgo["impacto"]]-1
                indice=(4-y)*5+x
                mapa[indice]+=1
            db.close()

        return templates.TemplateResponse(
            request=request,
            name="riesgo.html",
            context={
                "riesgos":riesgos,
                "procesos":procesos,
                "mapa":mapa,
                "flash":flash
            }
        )


    # --------------------------------------------------
    # RECOMENDAR CON IA
    # --------------------------------------------------

    @app.post("/riesgo/recomendar")
    async def recomendar_riesgo(request: Request):
        try:
            datos = await request.json()
        except Exception:
            return JSONResponse({"detail": "La solicitud no tiene un formato valido."}, status_code=400)

        nombre = (datos.get("nombre") or "").strip()
        descripcion = (datos.get("descripcion") or "").strip()

        if not nombre:
            return JSONResponse({"detail": "Ingrese el nombre del riesgo antes de usar IA."}, status_code=400)

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

        entrada = {
            "riesgo": {
                "nombre": texto_corto(nombre, 120),
                "descripcion_actual": texto_corto(descripcion, 300),
            },
            "valores_validos": {
                "impacto": list(valores_impacto.keys()),
                "probabilidad": list(valores_probabilidad.keys()),
            },
            "criterios": [
                "Cada solicitud es independiente y sin memoria.",
                "Usa solo el nombre y descripcion_actual recibidos.",
                "No menciones procesos, proyectos ni datos que no aparezcan en la entrada.",
                "Devuelve una descripcion profesional y concreta del riesgo.",
                "Selecciona impacto y probabilidad solo desde valores_validos.",
                "Explica brevemente por que seleccionaste ese impacto y esa probabilidad.",
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
                        "Eres especialista en gestion de riesgos para MAGERISK. "
                        "Ayudas a completar un formulario de riesgo. "
                        "Responde solo JSON valido con: descripcion, impacto, probabilidad, explicacion. "
                        "No inventes contexto externo ni uses memoria de solicitudes anteriores."
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

        impacto = str(recomendacion.get("impacto") or "").strip().upper()
        probabilidad = str(recomendacion.get("probabilidad") or "").strip().upper()
        if impacto not in valores_impacto:
            impacto = "MODERADO"
        if probabilidad not in valores_probabilidad:
            probabilidad = "POSIBLE"

        return JSONResponse(
            content=jsonable_encoder({
                "descripcion": texto_corto(recomendacion.get("descripcion"), 500),
                "impacto": impacto,
                "probabilidad": probabilidad,
                "nivel": calcular_nivel(impacto, probabilidad),
                "explicacion": texto_corto(recomendacion.get("explicacion"), 700),
            })
        )


    # --------------------------------------------------
    # CREAR
    # --------------------------------------------------

    @app.post("/crear_riesgo")
    async def crear_riesgo(request:Request):

        datos=await request.form()
        nombre=datos.get("nombre","").strip()
        descripcion=datos.get("descripcion","").strip()
        impacto=datos.get("impacto")
        probabilidad=datos.get("probabilidad", datos.get("frecuencia"))
        procesos=datos.getlist("procesos")
        response=RedirectResponse(
            "/riesgo",
            status_code=303
        )

        if nombre=="":

            set_flash(
                request,
                "warning",
                "Ingrese nombre."
            )
            return response

        db=conexion.conectar()

        if db=="":
            set_flash(
                request,
                "danger",
                "No se pudo conectar."
            )
            return response

        nivel=calcular_nivel(
            impacto,
            probabilidad
        )

        with db.cursor() as cursor:
            cursor.execute("""
            INSERT INTO riesgo(
                nombre,
                descripcion,
                impacto,
                frecuencia,
                nivel
            )
            VALUES(
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,(
                nombre,
                descripcion or None,
                impacto,
                probabilidad,
                nivel
            ))

            id_riesgo=cursor.lastrowid
            for proceso in procesos:
                cursor.execute("""
                INSERT INTO riesgo_proceso(
                    id_riesgo,
                    id_proceso
                )
                VALUES(
                    %s,
                    %s
                )
                """,(
                    id_riesgo,
                    proceso
                ))
            db.commit()
        db.close()

        set_flash(
            request,
            "success",
            "Riesgo registrado."
        )
        return response

    # --------------------------------------------------
    # EDITAR
    # --------------------------------------------------

    @app.post("/riesgo/{id}/editar")
    async def editar_riesgo(
        id:int,
        request:Request
    ):

        datos=await request.form()
        nombre=datos.get("nombre","").strip()
        descripcion=datos.get("descripcion","").strip()
        impacto=datos.get("impacto")
        probabilidad=datos.get("probabilidad", datos.get("frecuencia"))
        response=RedirectResponse(
            "/riesgo",
            status_code=303
        )

        if nombre=="":
            set_flash(
                request,
                "warning",
                "Ingrese nombre."
            )
            return response

        db=conexion.conectar()

        if db=="":
            set_flash(
                request,
                "danger",
                "No se pudo conectar."
            )
            return response

        nivel=calcular_nivel(
            impacto,
            probabilidad
        )

        with db.cursor() as cursor:
            cursor.execute("""
            UPDATE riesgo
            SET nombre=%s,
                descripcion=%s,
                impacto=%s,
                frecuencia=%s,
                nivel=%s
            WHERE id_riesgo=%s
            """,(
                nombre,
                descripcion or None,
                impacto,
                probabilidad,
                nivel,
                id
            ))
            db.commit()
        db.close()

        set_flash(
            request,
            "success",
            "Riesgo actualizado."
        )
        return response
    # --------------------------------------------------
    # ELIMINAR
    # --------------------------------------------------

    @app.post("/riesgo/{id}/eliminar")
    async def eliminar_riesgo(
        id:int,
        request:Request
    ):

        response=RedirectResponse(
            "/riesgo",
            status_code=303
        )
        db=conexion.conectar()
        if db=="":
            set_flash(
                request,
                "danger",
                "No se pudo conectar."
            )
            return response

        with db.cursor() as cursor:
            # Verificar si el riesgo tiene procesos asociados
            cursor.execute("""
                SELECT COUNT(*) AS total
                FROM riesgo_proceso
                WHERE id_riesgo = %s
            """, (id,))
            resultado = cursor.fetchone()
            if resultado["total"] > 0:

                db.close()
                set_flash(
                    request,
                    "warning",
                    "No se puede eliminar el riesgo porque tiene procesos asociados."
                )
                return response
            # Si no tiene procesos, eliminar el riesgo
            cursor.execute("""
            DELETE
            FROM riesgo
            WHERE id_riesgo=%s
            """,(id,))
            db.commit()
        db.close()

        set_flash(
            request,
            "success",
            "Riesgo eliminado."
        )
        return response


    # --------------------------------------------------
    # VER PROCESOS DE UN RIESGO
    # --------------------------------------------------

    @app.get("/riesgo/{id}/procesos")
    async def procesos_riesgo(id:int):

        db=conexion.conectar()
        procesos=[]
        if db!="":
            procesos=cargar_procesos_riesgo(
                db,
                id
            )
            db.close()
        return procesos
    
    @app.get("/riesgo/{id}/procesos_disponibles")
    async def procesos_disponibles(id:int):
        db = conexion.conectar()
        procesos = []
        if db != "":
            with db.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        id_proceso,
                        nombre
                    FROM proceso
                    WHERE id_proceso NOT IN(
                        SELECT id_proceso
                        FROM riesgo_proceso
                        WHERE id_riesgo=%s
                    )
                    ORDER BY nombre
                """,(id,))
                procesos = cursor.fetchall()
            db.close()
        return procesos


# --------------------------------------------------
# ASOCIAR PROCESO A RIESGO
# --------------------------------------------------

    @app.post("/riesgo/{id_riesgo}/agregar_proceso/{id_proceso}")
    async def agregar_proceso(
        id_riesgo: int,
        id_proceso: int
    ):
        db = conexion.conectar()
        if db == "":
            return {
                "ok": False
            }
        with db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO riesgo_proceso(
                    id_riesgo,
                    id_proceso
                )
                VALUES(
                    %s,
                    %s
                )
            """, (
                id_riesgo,
                id_proceso
            ))
            db.commit()
        db.close()
        return {
            "ok": True
        }
    
# --------------------------------------------------
# QUITAR PROCESO DE UN RIESGO
# --------------------------------------------------

    @app.post("/riesgo/{id_riesgo}/quitar_proceso/{id_proceso}")
    async def quitar_proceso(
        id_riesgo: int,
        id_proceso: int
    ):

        db = conexion.conectar()
        if db == "":
            return {
                "ok": False
            }
        with db.cursor() as cursor:
            cursor.execute("""
                DELETE
                FROM riesgo_proceso
                WHERE
                    id_riesgo=%s
                AND
                    id_proceso=%s
            """, (
                id_riesgo,
                id_proceso
            ))
            db.commit()
        db.close()
        return {
            "ok": True
        }
