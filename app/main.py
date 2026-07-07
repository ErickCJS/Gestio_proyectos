from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import conexion as conexion
from fastapi.responses import RedirectResponse
from routes  import usuario, procesos, riesgos

app = FastAPI()

templates = Jinja2Templates(directory="templates")
def usuario_actual(request):
    return request.session.get("usuario")

templates.env.globals["usuario_actual"] = usuario_actual

app.mount("/static", StaticFiles(directory="../static"), name="static")
app.add_middleware(
    SessionMiddleware,
    secret_key="mi_clave_super_secreta"
)

@app.get("/")
def inicio(request:Request):
    return templates.TemplateResponse(
        request=request,
        name="principal.html"
    )

@app.get('/dashboard')
def dashboard(request: Request):

    usuario = request.session.get("usuario")

    if not request.session.get("usuario"):
        return RedirectResponse(
            "/iniciar_sesion",
            status_code=302
        )

    mensaje = request.session.pop("mensaje", None)

    return templates.TemplateResponse(
        request=request,
        name="/maestras/dashboard.html",
        context={
            
            "usuario": usuario,
            "mensaje": mensaje
        }
    )

procesos.rutas(app, templates)
usuario.rutas(app, templates)
riesgos.rutas(app, templates)