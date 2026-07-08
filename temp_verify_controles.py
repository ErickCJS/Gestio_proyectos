from fastapi.templating import Jinja2Templates
from starlette.requests import Request

templates = Jinja2Templates(directory=r'c:\Users\ERICK\Documents\GitHub\Gestio_proyectos\app\templates')
scope = {'type':'http','method':'GET','path':'/controles','headers':[], 'query_string':b'', 'client':('127.0.0.1',1234), 'server':('testserver',80), 'scheme':'http', 'http_version':'1.1', 'root_path':'', 'app':None, 'session':{}}
request = Request(scope)
html = templates.get_template('controles.html').render(
    request=request,
    controles=[{'id_control':1,'nombre':'Prueba','descripcion':'Desc','tipo':'Preventivo','impacto':'Baja','probabilidad':'Media','estado':'Activo','riesgo_nombre':'Riesgo demo'}],
    riesgos=[{'id_riesgo':1,'nombre':'Riesgo demo'}],
    flash=None,
)
print('render_ok')
print('data-action' in html)
print('onclick=' in html)
print('mostrarDetalleControl(' in html)
