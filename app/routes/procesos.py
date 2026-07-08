from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
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
