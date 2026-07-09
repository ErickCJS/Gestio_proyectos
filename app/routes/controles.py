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
    opciones_efecto = {"No afecta", "Baja", "Media", "Alta", "Muy Alta"}

    def asegurar_tabla_control(db):
        # Se ha deshabilitado cualquier creación/alteración de tablas desde código Python
        # por petición del usuario. Esta función ahora es no-op para evitar DDL automáticos.
        return None

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
                    c.solidez_control,
                    c.mitigacion_probabilidad,
                    c.mitigacion_impacto,
                    c.nombre,
                    c.descripcion,
                    c.tipo,
                    c.estado,
                    c.fecha_creacion,
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

        print(controles)
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
        # solidez textual (enum)
        solidez = datos.get("solidez", "").strip()
        # mitigaciones en porcentaje 0-100 (enteros o null)
        mit_prob_raw = datos.get("mitigacion_probabilidad", "").strip()
        mit_imp_raw = datos.get("mitigacion_impacto", "").strip()
        try:
            mitigacion_prob = int(mit_prob_raw) if mit_prob_raw != '' else None
        except Exception:
            mitigacion_prob = None
        try:
            mitigacion_imp = int(mit_imp_raw) if mit_imp_raw != '' else None
        except Exception:
            mitigacion_imp = None
        id_riesgo = datos.get("id_riesgo", "").strip()

        response = RedirectResponse("/controles", status_code=303)

        if not nombre or not tipo or not id_riesgo:
            set_flash(request, "warning", "Complete los campos obligatorios.")
            return response

        if tipo not in tipos_control:
            set_flash(request, "warning", "Seleccione valores válidos para el control.")
            return response

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
                    id_riesgo,
                    solidez_control,
                    mitigacion_probabilidad,
                    mitigacion_impacto
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    nombre,
                    descripcion or None,
                    tipo,
                    id_riesgo,
                    solidez or 'Media',
                    mitigacion_prob,
                    mitigacion_imp,
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
        solidez = datos.get('solidez', '').strip()
        mit_prob_raw = datos.get('mitigacion_probabilidad', '').strip()
        mit_imp_raw = datos.get('mitigacion_impacto', '').strip()
        try:
            mitigacion_prob = int(mit_prob_raw) if mit_prob_raw != '' else None
        except Exception:
            mitigacion_prob = None
        try:
            mitigacion_imp = int(mit_imp_raw) if mit_imp_raw != '' else None
        except Exception:
            mitigacion_imp = None
        id_riesgo = datos.get('id_riesgo', '').strip()

        response = RedirectResponse('/controles', status_code=303)

        if not nombre or not tipo or not id_riesgo:
            set_flash(request, 'warning', 'Complete los campos obligatorios.')
            return response

        if tipo not in tipos_control:
            set_flash(request, 'warning', 'Seleccione valores válidos para el control.')
            return response

        db = conexion.conectar()
        if db == '':
            set_flash(request, 'danger', 'No se pudo conectar con la base de datos.')
            return response

        with db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE control
                SET nombre=%s, descripcion=%s, tipo=%s, id_riesgo=%s,
                    solidez_control=%s, mitigacion_probabilidad=%s, mitigacion_impacto=%s
                WHERE id_control=%s
                """,
                (nombre, descripcion or None, tipo, id_riesgo,
                 solidez or 'Media', mitigacion_prob, mitigacion_imp, id_control),
            )
            db.commit()

        db.close()
        set_flash(request, 'success', 'Control actualizado correctamente.')
        return response
