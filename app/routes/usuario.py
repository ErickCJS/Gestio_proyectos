from fastapi import Request, Form
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
import bcrypt
import re
try:
    from .. import conexion
except ImportError:
    import conexion


def rutas(app, templates):

    # ==========================
    # VISTA REGISTRAR
    # ==========================
    @app.get("/registrar")
    def registrar(request: Request):

        mensaje = request.session.pop("mensaje", None)
        datos = request.session.pop("datos", {})
                                    
        return templates.TemplateResponse(
            request=request,
            name="crear_cuenta.html",
            context={
                "request": request,
                "mensaje": mensaje,
                "datos": datos
            }
        )

    # ==========================
    # REGISTRAR USUARIO
    # ==========================
    @app.post("/registrar")
    def crear_usuario(
        request: Request,
        nombre: str = Form(...),
        correo: str = Form(...),
        password: str = Form(...)
    ):

        # Validaciones
        if nombre.strip() == "" or correo.strip() == "" or password.strip() == "":
            
            request.session["datos"] = {
                "nombre": nombre,
                "correo": correo
            }

            request.session["mensaje"] = {
                "tipo": "warning",
                "texto": "Complete todos los campos."
            }

            return RedirectResponse(
                "/registrar",
                status_code=302
            )
        
        if len(nombre) < 3:
            request.session["datos"] = {
                "nombre": nombre,
                "correo": correo
            }

            request.session["mensaje"] = {
                "tipo": "warning",
                "texto": "Ingrese un nombre válido."
            }

            request.session["datos"] = {
                "nombre": nombre,
                "correo": correo
            }

            return RedirectResponse(
                "/registrar",
                status_code=302
            )

        # -----------------------------
        # Validar correo
        # -----------------------------
        patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'

        if not re.match(patron, correo):

            request.session["datos"] = {
                "nombre": nombre,
                "correo": correo
            }

            request.session["mensaje"] = {
                "tipo": "warning",
                "texto": "Correo electrónico inválido."
            }

            return RedirectResponse(
                "/registrar",
                status_code=302
            )

        if len(password) < 8:
            request.session["datos"] = {
                "nombre": nombre,
                "correo": correo
            }
            
            request.session["mensaje"] = {
                "tipo": "warning",
                "texto": "La contraseña debe tener al menos 8 caracteres."
            }

            return RedirectResponse(
                "/registrar",
                status_code=302
            )
        if password.isalpha():

            request.session["datos"] = {
                "nombre": nombre,
                "correo": correo
            }
            
            request.session["mensaje"] = {
                "tipo": "warning",
                "texto": "Agregue al menos un número."
            }

            return RedirectResponse(
                "/registrar",
                status_code=302
            )

        if password.isnumeric():

            request.session["datos"] = {
                "nombre": nombre,
                "correo": correo
            }
            
            request.session["mensaje"] = {
                "tipo": "warning",
                "texto": "Agregue al menos una letra."
            }

            return RedirectResponse(
                "/registrar",
                status_code=302
            )

        db = conexion.conectar()

        if db == "":

            request.session["datos"] = {
                "nombre": nombre,
                "correo": correo
            }

            request.session["mensaje"] = {
                "tipo": "danger",
                "texto": "Error al conectar con la base de datos."
            }

            return RedirectResponse(
                "/registrar",
                status_code=302
            )

        with db.cursor() as cursor:

            cursor.execute(
                "SELECT id FROM usuario WHERE correo=%s",
                (correo,)
            )

            existe = cursor.fetchone()

            if existe:

                db.close()

                request.session["datos"] = {
                    "nombre": nombre,
                    "correo": correo
                }

                request.session["mensaje"] = {
                    "tipo": "danger",
                    "texto": "El correo ingresado ya está registrado."
                }

                return RedirectResponse(
                    "/registrar",
                    status_code=302
                )

            password_hash = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")

            cursor.execute(
                """
                INSERT INTO usuario
                (
                    correo,
                    password,
                    nombres_completo
                )
                VALUES
                (
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    correo,
                    password_hash,
                    nombre
                )
            )

            db.commit()

        db.close()
        
        request.session.pop("datos", None)

        request.session["mensaje"] = {
            "tipo": "success",
            "texto": "Cuenta creada correctamente."
        }

        return RedirectResponse(
            "/iniciar_sesion",
            status_code=302
        )


    # ==========================
    # VISTA LOGIN
    # ==========================
    @app.get("/iniciar_sesion")
    def vista_login(request: Request):

        mensaje = request.session.pop("mensaje", None)
        datos = request.session.pop("datos", {})

        return templates.TemplateResponse(
            request=request,
            name="inicio_sesion.html",
            context={
                "request": request,
                "mensaje": mensaje,
                "datos": datos
            }
        )

    # ==========================
    # LOGIN
    # ==========================
    @app.post("/iniciar_sesion")
    def login(
        request: Request,
        correo: str = Form(...),
        password: str = Form(...)
    ):

        if correo.strip() == "" or password.strip() == "":

            request.session["datos"] = {
                "correo": correo
            }
            
            request.session["mensaje"] = {
                "tipo": "danger",
                "texto": "Complete todos los campos."
            }

            return RedirectResponse(
                "/iniciar_sesion",
                status_code=302
            )

        db = conexion.conectar()

        if db == "":

            request.session["datos"] = {
                "correo": correo
            }

            
            request.session["mensaje"] = {
                "tipo": "danger",
                "texto": "No se pudo conectar con la base de datos."
            }

            return RedirectResponse(
                "/iniciar_sesion",
                status_code=302
            )

        with db.cursor() as cursor:

            cursor.execute(
                "SELECT * FROM usuario WHERE correo=%s",
                (correo,)
            )

            usuario = cursor.fetchone()

        db.close()

        if usuario is None:

            request.session["datos"] = {
                "correo": correo
            }
            
            request.session["mensaje"] = {
                "tipo": "danger",
                "texto": "El correo ingresado no se encuentra registrado."
            }

            return RedirectResponse(
                "/iniciar_sesion",
                status_code=302
            )

        if not bcrypt.checkpw(
            password.encode("utf-8"),
            usuario["password"].encode("utf-8")
        ):

            request.session["datos"] = {
                "correo": correo
            }

            request.session["mensaje"] = {
                "tipo": "danger",
                "texto": "Contraseña incorrecta."
            }

            return RedirectResponse(
                "/iniciar_sesion",
                status_code=302
            )

        request.session["usuario"] = {
            "id": usuario["id"],
            "nombre": usuario["nombres_completo"],
            "correo": usuario["correo"]
        }

        request.session["mensaje"] = {
            "tipo": "success",
            "texto": f"Bienvenido, {usuario['nombres_completo']}."
        }

        return RedirectResponse(
            "/dashboard",
            status_code=302
        )

    # ==========================
    # BUSCAR PERSONAS
    # ==========================
    @app.get("/personas/buscar")
    def buscar_personas(q: str = ""):
        termino = q.strip()

        if termino == "":
            return JSONResponse([])

        db = conexion.conectar()
        if db == "":
            return JSONResponse([])

        personas = []

        with db.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    nombres_completo,
                    correo
                FROM usuario
                WHERE nombres_completo LIKE %s
                   OR correo LIKE %s
                ORDER BY nombres_completo ASC
                LIMIT 10
                """,
                (f"%{termino}%", f"%{termino}%")
            )
            personas = cursor.fetchall()

        db.close()
        return JSONResponse(personas)


    # ==========================
    # CERRAR SESIÓN
    # ==========================
    @app.get("/cerrar_sesion")
    def cerrar_sesion(request: Request):

        request.session.clear()

        return RedirectResponse(
            "/",
            status_code=302
        )
