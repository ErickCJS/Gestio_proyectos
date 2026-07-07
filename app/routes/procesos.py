from fastapi import  Request
from fastapi.responses import RedirectResponse

def rutas(app, templates):

    @app.get('/procesos')
    async def procesos(request:Request):
        return templates.TemplateResponse(
            name = "procesos.html",
            request=request
        )
    
    @app.get("/grupos")
    async def grupos(request: Request):

        success = request.cookies.get('mensaje')

        response =  templates.TemplateResponse(
            request=request,
            name="grupos.html",
            context={
                "mensaje" : success
            }
        )
        if success: 
            response.delete_cookie("mensaje")

        return response


    @app.post("/crear_grupo")
    async def crear_grupo(request: Request):

        datos = await request.form()

        nombre = datos.get("nombre", "").strip()
        descripcion = datos.get('descripcion', '').strip()

        response = RedirectResponse("/grupos", status_code=303)

        if not nombre:
            response.set_cookie(
                key="mensaje",
                value="El nombre es obligatorio",
                max_age=5  # segundos
            )
            return response

        if not descripcion:
            response.set_cookie(
                key="mensaje",
                value="La descripcion es obligatorio",
                max_age=5  # segundos
            )
            return response
        # Guardar en BD...

        response.set_cookie(
            key="mensaje",
            value="Grupo creado correctamente",
            max_age=5  # segundos
        )
        return response