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
            "texto": texto,
        }

    tipos_control = {"Preventivo", "Detectivo", "Correctivo"}
    solidez_opciones = {"Muy baja", "Baja", "Media", "Alta", "Muy alta"}

    def asegurar_tabla_control(db):
        columnas = {
            "maximo_baja_probabilidad": "DECIMAL(5,2) NOT NULL DEFAULT 100",
            "maximo_baja_impacto": "DECIMAL(5,2) NOT NULL DEFAULT 100",
        }
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'control'
            """)
            existentes = {fila["COLUMN_NAME"] for fila in cursor.fetchall()}
            for columna, definicion in columnas.items():
                if columna not in existentes:
                    cursor.execute(f"ALTER TABLE control ADD COLUMN {columna} {definicion}")
        db.commit()

    def porcentaje_formulario(valor, defecto=0):
        try:
            numero = float(valor if valor not in (None, "") else defecto)
        except (TypeError, ValueError):
            numero = defecto
        return max(0, min(100, numero))

    def cargar_riesgos(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id_riesgo,
                    nombre
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
                    c.maximo_baja_probabilidad,
                    c.maximo_baja_impacto,
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

    @app.get("/controles")
    async def controles(request: Request):
        flash = request.session.pop("flash", None)
        db = conexion.conectar()
        controles = []
        riesgos = []

        if db != "":
            asegurar_tabla_control(db)
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

    @app.post("/crear_control")
    async def crear_control(request: Request):
        datos = await request.form()
        nombre = datos.get("nombre", "").strip()
        descripcion = datos.get("descripcion", "").strip()
        tipo = datos.get("tipo", "").strip()
        solidez_control = datos.get("solidez_control", "Media").strip()
        maximo_baja_probabilidad = datos.get("maximo_baja_probabilidad", "100").strip()
        maximo_baja_impacto = datos.get("maximo_baja_impacto", "100").strip()
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

        maximo_baja_probabilidad = porcentaje_formulario(maximo_baja_probabilidad, 100)
        maximo_baja_impacto = porcentaje_formulario(maximo_baja_impacto, 100)
        mitigacion_probabilidad = porcentaje_formulario(mitigacion_probabilidad, 0)
        mitigacion_impacto = porcentaje_formulario(mitigacion_impacto, 0)

        db = conexion.conectar()
        if db == "":
            set_flash(request, "danger", "No se pudo conectar con la base de datos.")
            return response

        with db.cursor() as cursor:
            asegurar_tabla_control(db)
            cursor.execute(
                """
                INSERT INTO control (
                    nombre,
                    descripcion,
                    tipo,
                    solidez_control,
                    maximo_baja_probabilidad,
                    maximo_baja_impacto,
                    mitigacion_probabilidad,
                    mitigacion_impacto,
                    id_riesgo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    nombre,
                    descripcion or None,
                    tipo,
                    solidez_control,
                    maximo_baja_probabilidad,
                    maximo_baja_impacto,
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
        maximo_baja_probabilidad = datos.get('maximo_baja_probabilidad', '100').strip()
        maximo_baja_impacto = datos.get('maximo_baja_impacto', '100').strip()
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

        maximo_baja_probabilidad = porcentaje_formulario(maximo_baja_probabilidad, 100)
        maximo_baja_impacto = porcentaje_formulario(maximo_baja_impacto, 100)
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
                    maximo_baja_probabilidad=%s,
                    maximo_baja_impacto=%s,
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
                    maximo_baja_probabilidad,
                    maximo_baja_impacto,
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
