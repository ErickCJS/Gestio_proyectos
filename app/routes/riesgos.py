from fastapi import Request
from fastapi.responses import RedirectResponse
import conexion


def rutas(app, templates):

    @app.get("/riesgo")
    async def procesos(request: Request):


        return templates.TemplateResponse(
            name="riesgo.html",
            request=request,
        )