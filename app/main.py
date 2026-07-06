from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware


app = FastAPI()

templates = Jinja2Templates(directory="templates")
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


@app.get("/iniciar_sesion")
def inicio(request:Request):
    return templates.TemplateResponse(
        request=request,
        name="inicio_sesion.html"
    )

@app.get("/registrar")
def inicio(request:Request):
    return templates.TemplateResponse(
        request=request,
        name="crear_cuenta.html"
    )


@app.get('/dashboard')
def dashboard(request:Request):
    return templates.TemplateResponse(
        name = "/maestras/dashboard.html",
        request=request
    )