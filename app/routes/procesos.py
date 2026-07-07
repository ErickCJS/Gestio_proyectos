from fastapi import Request
from fastapi.responses import RedirectResponse
import conexion


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
            sembrar_procesos_si_vacio(db)
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
            db.commit()

        db.close()
        set_flash(request, "success", "Proceso creado correctamente.")
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

    @app.get("/grupos")
    async def grupos(request: Request):
        flash = request.session.pop("flash", None)
        db = conexion.conectar()
        grupos = []

        if db != "":
            with db.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id_grupo,
                        nombre,
                        descripcion
                    FROM grupo
                    ORDER BY id_grupo DESC
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
