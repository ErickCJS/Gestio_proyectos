from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse

try:
    from .routes import usuario, procesos, riesgos, controles
except ImportError:
    from routes import usuario, procesos, riesgos, controles

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
def usuario_actual(request):
    return request.session.get("usuario")

templates.env.globals["usuario_actual"] = usuario_actual

app.mount("/static", StaticFiles(directory=str(BASE_DIR.parent / "static")), name="static")
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
controles.rutas(app, templates)
