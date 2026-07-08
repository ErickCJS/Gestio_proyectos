from fastapi import Request
from fastapi.responses import RedirectResponse
try:
    from .. import conexion
except ImportError:
    import conexion


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

    valores_frecuencia = {
        "RARA":1,
        "IMPROBABLE":2,
        "POSIBLE":3,
        "PROBABLE":4,
        "CASI_SEGURO":5
    }


    def calcular_nivel(impacto, frecuencia):

        total = (
            valores_impacto[impacto] *
            valores_frecuencia[frecuencia]
        )
        if total <=4:
            return "BAJO"
        elif total<=9:
            return "MEDIO"
        elif total<=16:
            return "ALTO"
        return "EXTREMO"

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
                riesgo["procesos"]=cargar_procesos_riesgo(
                    db,
                    riesgo["id_riesgo"]
                )
            mapa=[0]*25
            for riesgo in riesgos:
                x=valores_frecuencia[riesgo["frecuencia"]]-1
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
    # CREAR
    # --------------------------------------------------

    @app.post("/crear_riesgo")
    async def crear_riesgo(request:Request):

        datos=await request.form()
        nombre=datos.get("nombre","").strip()
        descripcion=datos.get("descripcion","").strip()
        impacto=datos.get("impacto")
        frecuencia=datos.get("frecuencia")
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
            frecuencia
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
                frecuencia,
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
