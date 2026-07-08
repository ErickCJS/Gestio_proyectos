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

    def asegurar_tabla_control(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS control (
                    id_control INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(150) NOT NULL,
                    descripcion VARCHAR(255),
                    tipo ENUM('Preventivo', 'Detectivo', 'Correctivo') NOT NULL,
                    id_riesgo INT NOT NULL,
                    id_proceso INT NULL,
                    estado ENUM('Activo', 'Inactivo') NOT NULL DEFAULT 'Activo',
                    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_control_riesgo
                        FOREIGN KEY (id_riesgo)
                        REFERENCES riesgo(id_riesgo),
                    CONSTRAINT fk_control_proceso
                        FOREIGN KEY (id_proceso)
                        REFERENCES proceso(id_proceso)
                )
                """
            )
            db.commit()

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

    def cargar_procesos(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id_proceso,
                    nombre
                FROM proceso
                ORDER BY nombre ASC
                """
            )
            return cursor.fetchall()

    def cargar_controles(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id_control,
                    c.nombre,
                    c.descripcion,
                    c.tipo,
                    c.estado,
                    c.fecha_creacion,
                    r.nombre AS riesgo_nombre,
                    p.nombre AS proceso_nombre
                FROM control c
                INNER JOIN riesgo r
                    ON r.id_riesgo = c.id_riesgo
                LEFT JOIN proceso p
                    ON p.id_proceso = c.id_proceso
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
        procesos = []

        if db != "":
            asegurar_tabla_control(db)
            riesgos = cargar_riesgos(db)
            procesos = cargar_procesos(db)
            controles = cargar_controles(db)
            db.close()

        return templates.TemplateResponse(
            name="controles.html",
            request=request,
            context={
                "flash": flash,
                "controles": controles,
                "riesgos": riesgos,
                "procesos": procesos,
            },
        )

    @app.post("/crear_control")
    async def crear_control(request: Request):
        datos = await request.form()
        nombre = datos.get("nombre", "").strip()
        descripcion = datos.get("descripcion", "").strip()
        tipo = datos.get("tipo", "").strip()
        id_riesgo = datos.get("id_riesgo", "").strip()
        id_proceso = datos.get("id_proceso", "").strip()

        response = RedirectResponse("/controles", status_code=303)

        if not nombre or not tipo or not id_riesgo:
            set_flash(request, "warning", "Complete los campos obligatorios.")
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
                    id_proceso
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    nombre,
                    descripcion or None,
                    tipo,
                    id_riesgo,
                    id_proceso or None,
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
