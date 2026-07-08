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
        with db.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS control (
                    id_control INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(150) NOT NULL,
                    descripcion VARCHAR(255),
                    tipo ENUM('Preventivo', 'Detectivo', 'Correctivo') NOT NULL,
                    impacto ENUM('No afecta', 'Baja', 'Media', 'Alta', 'Muy Alta') NOT NULL DEFAULT 'No afecta',
                    probabilidad ENUM('No afecta', 'Baja', 'Media', 'Alta', 'Muy Alta') NOT NULL DEFAULT 'No afecta',
                    id_riesgo INT NOT NULL,
                    estado ENUM('Activo', 'Inactivo') NOT NULL DEFAULT 'Activo',
                    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_control_riesgo
                        FOREIGN KEY (id_riesgo)
                        REFERENCES riesgo(id_riesgo)
                )
                """
            )
            columnas = {
                "impacto": """
                    ALTER TABLE control
                    ADD COLUMN impacto ENUM('No afecta', 'Baja', 'Media', 'Alta', 'Muy Alta') NOT NULL DEFAULT 'No afecta'
                """,
                "probabilidad": """
                    ALTER TABLE control
                    ADD COLUMN probabilidad ENUM('No afecta', 'Baja', 'Media', 'Alta', 'Muy Alta') NOT NULL DEFAULT 'No afecta'
                """
            }
            for columna, ddl in columnas.items():
                cursor.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                        AND TABLE_NAME = 'control'
                        AND COLUMN_NAME = %s
                    """,
                    (columna,),
                )
                if cursor.fetchone()["total"] == 0:
                    cursor.execute(ddl)
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

    def cargar_controles(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.id_control,
                    c.nombre,
                    c.descripcion,
                    c.tipo,
                    c.impacto,
                    c.probabilidad,
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
        impacto = datos.get("impacto", "").strip()
        probabilidad = datos.get("probabilidad", "").strip()
        id_riesgo = datos.get("id_riesgo", "").strip()

        response = RedirectResponse("/controles", status_code=303)

        if not nombre or not tipo or not impacto or not probabilidad or not id_riesgo:
            set_flash(request, "warning", "Complete los campos obligatorios.")
            return response

        if tipo not in tipos_control or impacto not in opciones_efecto or probabilidad not in opciones_efecto:
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
                    impacto,
                    probabilidad,
                    id_riesgo
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    nombre,
                    descripcion or None,
                    tipo,
                    impacto,
                    probabilidad,
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
