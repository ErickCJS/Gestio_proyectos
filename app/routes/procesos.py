from fastapi import Request
from fastapi.responses import RedirectResponse
import conexion


def rutas(app, templates):

    def cargar_catalogos(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, nombre
                FROM proyecto
                ORDER BY id DESC
                """
            )
            proyectos = cursor.fetchall()

            cursor.execute(
                """
                SELECT id_grupo, nombre
                FROM grupo
                ORDER BY id_grupo DESC
                """
            )
            grupos = cursor.fetchall()

        return proyectos, grupos

    def cargar_procesos(db):
        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    p.id_proceso,
                    p.codigo,
                    p.nombre,
                    p.descripcion,
                    p.estado,
                    p.fecha_creacion,
                    pr.nombre AS proyecto_nombre,
                    g.nombre AS grupo_nombre,
                    p.id_proyecto,
                    p.id_grupo
                FROM proceso p
                INNER JOIN proyecto pr ON pr.id = p.id_proyecto
                INNER JOIN grupo g ON g.id_grupo = p.id_grupo
                ORDER BY p.id_proceso DESC
                """
            )
            return cursor.fetchall()

    @app.get("/procesos")
    async def procesos(request: Request):
        flash = request.session.pop("flash", None)
        db = conexion.conectar()
        procesos = []
        proyectos = []
        grupos = []

        if db != "":
            with db.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS proceso (
                        id_proceso INT AUTO_INCREMENT PRIMARY KEY,
                        codigo VARCHAR(20) NOT NULL UNIQUE,
                        nombre VARCHAR(150) NOT NULL,
                        descripcion VARCHAR(255),
                        id_proyecto INT NOT NULL,
                        id_grupo INT NOT NULL,
                        estado ENUM('ACTIVO','INACTIVO') NOT NULL DEFAULT 'ACTIVO',
                        fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT fk_proceso_proyecto
                            FOREIGN KEY (id_proyecto)
                            REFERENCES proyecto(id),
                        CONSTRAINT fk_proceso_grupo
                            FOREIGN KEY (id_grupo)
                            REFERENCES grupo(id_grupo)
                    )
                    """
                )
                db.commit()

            proyectos, grupos = cargar_catalogos(db)
            procesos = cargar_procesos(db)
            db.close()

        return templates.TemplateResponse(
            name="procesos.html",
            request=request,
            context={
                "flash": flash,
                "procesos": procesos,
                "proyectos": proyectos,
                "grupos": grupos,
            },
        )

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
                        descripcion,
                        estado
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
            request.session["flash"] = "El nombre es obligatorio."
            return response

        db = conexion.conectar()
        if db == "":
            request.session["flash"] = "No se pudo conectar con la base de datos."
            return response

        with db.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS grupo (
                    id_grupo INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    descripcion VARCHAR(255) NULL,
                    estado ENUM('ACTIVO','INACTIVO') NOT NULL DEFAULT 'ACTIVO',
                    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                INSERT INTO grupo (nombre, descripcion, estado)
                VALUES (%s, %s, %s)
                """,
                (nombre, descripcion or None, "ACTIVO"),
            )
            db.commit()

        db.close()
        request.session["flash"] = "Grupo creado correctamente."
        return response

    @app.post("/grupo/{id_grupo}/alternar")
    async def alternar_grupo(id_grupo: int, request: Request):
        response = RedirectResponse("/grupos", status_code=303)
        db = conexion.conectar()

        if db == "":
            request.session["flash"] = "No se pudo conectar con la base de datos."
            return response

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT estado FROM grupo WHERE id_grupo=%s",
                (id_grupo,),
            )
            grupo = cursor.fetchone()
            if grupo is None:
                db.close()
                request.session["flash"] = "El grupo no existe."
                return response

            nuevo_estado = "INACTIVO" if grupo["estado"] == "ACTIVO" else "ACTIVO"
            cursor.execute(
                "UPDATE grupo SET estado=%s WHERE id_grupo=%s",
                (nuevo_estado, id_grupo),
            )
            db.commit()

        db.close()
        request.session["flash"] = "Estado del grupo actualizado."
        return response

    @app.post("/grupo/{id_grupo}/eliminar")
    async def eliminar_grupo(id_grupo: int, request: Request):
        response = RedirectResponse("/grupos", status_code=303)
        db = conexion.conectar()

        if db == "":
            request.session["flash"] = "No se pudo conectar con la base de datos."
            return response

        with db.cursor() as cursor:
            cursor.execute(
                "DELETE FROM grupo WHERE id_grupo=%s",
                (id_grupo,),
            )
            db.commit()

        db.close()
        request.session["flash"] = "Grupo eliminado correctamente."
        return response

    @app.post("/crear_proceso")
    async def crear_proceso(request: Request):
        datos = await request.form()
        codigo = datos.get("codigo", "").strip()
        nombre = datos.get("nombre", "").strip()
        descripcion = datos.get("descripcion", "").strip()
        id_proyecto = datos.get("id_proyecto", "").strip()
        id_grupo = datos.get("id_grupo", "").strip()

        response = RedirectResponse("/procesos", status_code=303)

        if not codigo or not nombre or not id_proyecto or not id_grupo:
            request.session["flash"] = "Complete los campos obligatorios."
            return response

        db = conexion.conectar()
        if db == "":
            request.session["flash"] = "No se pudo conectar con la base de datos."
            return response

        with db.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS proceso (
                    id_proceso INT AUTO_INCREMENT PRIMARY KEY,
                    codigo VARCHAR(20) NOT NULL UNIQUE,
                    nombre VARCHAR(150) NOT NULL,
                    descripcion VARCHAR(255),
                    id_proyecto INT NOT NULL,
                    id_grupo INT NOT NULL,
                    estado ENUM('ACTIVO','INACTIVO') NOT NULL DEFAULT 'ACTIVO',
                    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_proceso_proyecto
                        FOREIGN KEY (id_proyecto)
                        REFERENCES proyecto(id),
                    CONSTRAINT fk_proceso_grupo
                        FOREIGN KEY (id_grupo)
                        REFERENCES grupo(id_grupo)
                )
                """
            )

            cursor.execute(
                """
                INSERT INTO proceso (codigo, nombre, descripcion, id_proyecto, id_grupo, estado)
                VALUES (%s, %s, %s, %s, %s, 'ACTIVO')
                """,
                (codigo, nombre, descripcion or None, id_proyecto, id_grupo),
            )
            db.commit()

        db.close()
        request.session["flash"] = "Proceso creado correctamente."
        return response

    @app.post("/procesos/{id_proceso}/alternar")
    async def alternar_proceso(id_proceso: int, request: Request):
        response = RedirectResponse("/procesos", status_code=303)
        db = conexion.conectar()

        if db == "":
            request.session["flash"] = "No se pudo conectar con la base de datos."
            return response

        with db.cursor() as cursor:
            cursor.execute(
                "SELECT estado FROM proceso WHERE id_proceso=%s",
                (id_proceso,),
            )
            proceso = cursor.fetchone()
            if proceso is None:
                db.close()
                request.session["flash"] = "El proceso no existe."
                return response

            nuevo_estado = "INACTIVO" if proceso["estado"] == "ACTIVO" else "ACTIVO"
            cursor.execute(
                "UPDATE proceso SET estado=%s WHERE id_proceso=%s",
                (nuevo_estado, id_proceso),
            )
            db.commit()

        db.close()
        request.session["flash"] = "Estado del proceso actualizado."
        return response

    @app.post("/procesos/{id_proceso}/eliminar")
    async def eliminar_proceso(id_proceso: int, request: Request):
        response = RedirectResponse("/procesos", status_code=303)
        db = conexion.conectar()

        if db == "":
            request.session["flash"] = "No se pudo conectar con la base de datos."
            return response

        with db.cursor() as cursor:
            cursor.execute(
                "DELETE FROM proceso WHERE id_proceso=%s",
                (id_proceso,),
            )
            db.commit()

        db.close()
        request.session["flash"] = "Proceso eliminado correctamente."
        return response
