from fastapi import FastAPI, Request

def rutas(app, templates):

    @app.get('/procesos')
    def procesos(request:Request):
        return templates.TemplateResponse(
            name = "procesos.html",
            request=request
        )