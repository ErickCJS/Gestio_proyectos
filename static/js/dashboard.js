let estado_sider = localStorage.getItem('estado_sider') ?? 1;
var sidebar = document.getElementById('sidebar');
var mainContent = document.getElementById('mainContent');
var menu = document.getElementById('btnToggleSidebar');
var brn_cerrarsider = document.getElementById('sidebarClose');
var el_modal = document.getElementById('projectModal');
var modal = new bootstrap.Modal(el_modal);
const modal_titulo = document.getElementById('projectModalLabel');
const modal_cuerpo = document.getElementById('cuerpo_modal');
const modal_footer = document.getElementById('modal_footer');

const accion_estado = () => {
    if (estado_sider == 1){
        sidebar.classList.remove('oculto');
        mainContent.classList.remove('expanded')
    }else{
        sidebar.classList.add('oculto');
        mainContent.classList.add('expanded')
    }
}
accion_estado();

const accion_menu = () => {
    estado_sider = estado_sider == 1 ? 0 : 1 ;
    localStorage.setItem('estado_sider', estado_sider);
    accion_estado();
}

const cerrar_sider = () => {
    estado_sider = 0;
    localStorage.setItem('estado_sider', estado_sider);
    accion_estado();
}

const mostrar_modal = (tipo, data = {}) => {
    var html = '';
    var titulo = "";
    var botones = "";

    switch (tipo) {
        case 'pry_nuevo':
            titulo = "Crear Proyecto";
            botones = `
                <button onclick="cerrar_modal()" type="button" class="btn btn-sm btn-secondary">Cancelar</button>
                <button type="button" class="btn btn-sm btn_primario">Guardar</button>
            `;
            html = `
                <form id="projectForm">
                    <div class="mb-3">
                        <label for="projectName" class="form-label modal-label">Nombre del proyecto</label>
                        <input type="text" class="form-control" id="projectName" name="projectName" placeholder="Ingrese nombre" required>
                    </div>
                    <div class="mb-3">
                        <label for="projectDesc" class="form-label modal-label">Descripción</label>
                        <textarea class="form-control" id="projectDesc" name="projectDesc" rows="3" placeholder="Descripción opcional"></textarea>
                    </div>
                </form>
            `;
            break;

        case 'ngrupo':
            titulo = "Crear Grupo";
            botones = `
                <button type="button" class="btn btn-sm btn-secondary" onclick="cerrar_modal()">Cancelar</button>
                <button type="submit" class="btn btn-sm btn_primario" form="frm_creargrupo">
                    <i class="bi bi-floppy me-2"></i>
                    Guardar grupo
                </button>
            `;
            html = `
                <form id="frm_creargrupo" method="post" action="/crear_grupo">
                    <div class="mb-3">
                        <label class="form-label modal-label">Nombre del grupo</label>
                        <div class="input-group">
                            <span class="input-group-text"><i class="bi bi-people"></i></span>
                            <input type="text" class="form-control" name="nombre" placeholder="Ej. Tecnología de la Información" maxlength="100" required>
                        </div>
                    </div>
                    <div class="mb-2">
                        <label class="form-label modal-label">Descripción</label>
                        <div class="input-group">
                            <span class="input-group-text"><i class="bi bi-card-text"></i></span>
                            <textarea class="form-control" name="descripcion" rows="4" maxlength="255" placeholder="Describe la función o responsabilidad del grupo."></textarea>
                        </div>
                    </div>
                </form>
            `;
            break;

        case 'nproceso': {
            titulo = "Crear Proceso";
            const grupos = (window.catalogosProcesos && window.catalogosProcesos.grupos) ? window.catalogosProcesos.grupos : [];
            const opcionesGrupos = grupos.map(item => `<option value="${item.id_grupo}">${item.nombre}</option>`).join('');
            botones = `
                <button type="button" class="btn btn-sm btn-secondary" onclick="cerrar_modal()">Cancelar</button>
                <button type="submit" class="btn btn-sm btn_primario" form="frm_crearproceso">
                    <i class="bi bi-floppy me-2"></i>
                    Guardar proceso
                </button>
            `;
            html = `
                <form id="frm_crearproceso" method="post" action="/crear_proceso">
                    <div class="mb-3">
                        <label class="form-label modal-label">Nombre del proceso</label>
                        <input type="text" class="form-control" name="nombre" placeholder="Ej. Gestión de Matrículas" maxlength="150" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Descripción</label>
                        <textarea class="form-control" name="descripcion" rows="3" maxlength="255" placeholder="Descripción opcional"></textarea>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Grupo responsable</label>
                        <select class="form-select" name="id_grupo" required>
                            <option value="">Seleccione un grupo</option>
                            ${opcionesGrupos}
                        </select>
                    </div>
                </form>
            `;
            break;
        }

        case 'ver_grupo':
            titulo = `Grupo #${String(data.id_grupo).padStart(3, '0')}`;
            botones = `
                <button type="button" class="btn btn-sm btn-secondary" onclick="cerrar_modal()">Cerrar</button>
            `;
            html = `
                <div class="mb-3">
                    <label class="form-label modal-label">Nombre</label>
                    <div class="modal-readonly-field">${data.nombre ?? ''}</div>
                </div>
                <div class="mb-3">
                    <label class="form-label modal-label">Descripción</label>
                    <div class="modal-readonly-field modal-readonly-multiline">${data.descripcion ?? ''}</div>
                </div>
            `;
            break;

        case 'ver_proceso':
            titulo = `Proceso #${String(data.id_proceso).padStart(3, '0')}`;
            botones = `
                <button type="button" class="btn btn-sm btn-secondary" onclick="cerrar_modal()">Cerrar</button>
            `;
            html = `
                <div class="mb-3">
                    <label class="form-label modal-label">Código</label>
                    <div class="modal-readonly-field">PRC-${String(data.id_proceso).padStart(3, '0')}</div>
                </div>
                <div class="mb-3">
                    <label class="form-label modal-label">Nombre</label>
                    <div class="modal-readonly-field">${data.nombre ?? ''}</div>
                </div>
                <div class="mb-3">
                    <label class="form-label modal-label">Descripción</label>
                    <div class="modal-readonly-field modal-readonly-multiline">${data.descripcion ?? ''}</div>
                </div>
                <div class="mb-3">
                    <label class="form-label modal-label">Grupo</label>
                    <div class="modal-readonly-field">${data.grupo_nombre ?? ''}</div>
                </div>
            `;
            break;

        default:
            break;
    }

    modal_footer.innerHTML = botones;
    modal_cuerpo.innerHTML = html;
    modal_titulo.innerHTML = titulo;
    modal.show();
}

const cerrar_modal = () => {
    modal.hide();
}

const ver_grupo = (id_grupo, nombre, descripcion) => {
    mostrar_modal('ver_grupo', {
        id_grupo,
        nombre,
        descripcion,
    });
}

const ver_proceso = (id_proceso, nombre, descripcion, grupo_nombre) => {
    mostrar_modal('ver_proceso', {
        id_proceso,
        nombre,
        descripcion,
        grupo_nombre
    });
}

const eliminarGrupo = async (id_grupo) => {
    if (!confirm('¿Seguro que deseas eliminar este grupo?')) {
        return;
    }

    try {
        const respuesta = await fetch(`/grupo/${id_grupo}/eliminar`, {
            method: 'POST'
        });

        if (!respuesta.ok) {
            throw new Error('No se pudo eliminar el grupo');
        }

        window.location.reload();
    } catch (error) {
        alert(error.message);
    }
}

const eliminarProceso = async (id_proceso) => {
    if (!confirm('¿Seguro que deseas eliminar este proceso?')) {
        return;
    }

    try {
        const respuesta = await fetch(`/procesos/${id_proceso}/eliminar`, {
            method: 'POST'
        });

        if (!respuesta.ok) {
            throw new Error('No se pudo eliminar el proceso');
        }

        window.location.reload();
    } catch (error) {
        alert(error.message);
    }
}

brn_cerrarsider.addEventListener('click', function (){
    cerrar_sider();
})

menu.addEventListener('click', function(){
    accion_menu();
})
