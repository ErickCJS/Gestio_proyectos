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

//procedimiento

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

const mostrar_modal = (tipo) => {
    var html = '';
    var titulo = "";
    var botones = "";
    switch (tipo) {
        case 'pry_nuevo':
            titulo = "Crear Proyecto";
            botones = `
                <button onclick="cerrar_modal()" type="button" class="btn btn-sm btn-secondary" id="saveProjectBtn">Cancelar</button>
                <button type="button" class="btn btn-sm btn_primario" id="saveProjectBtn">Guardar</button>
            `;
            html = `
                    <form id="projectForm">
                        <div class="mb-3">
                            <label for="projectName" class="form-label">Nombre del proyecto</label>
                            <input type="text" class="form-control" id="projectName" name="projectName" placeholder="Ingrese nombre" required>
                        </div>
                        <div class="mb-3">
                            <label for="projectDesc" class="form-label">Descripción</label>
                            <textarea class="form-control" id="projectDesc" name="projectDesc" rows="3" placeholder="Descripción opcional"></textarea>
                        </div>
                    </form>
                `;
            break;
        case 'ngrupo':
            titulo = "Crear Grupo";
            botones = `
                <button type="reset" class="btn btn-sm btn-secondary" >
                    Cancelar
                </button>

                <button type="submit" class="btn btn-sm btn_primario" form="frm_creargrupo">
                    <i class="bi bi-floppy me-2"></i>
                    Guardar grupo
                </button>
            `;
            html = `
                <form id="frm_creargrupo" method="post" action="/crear_grupo">
                    <div class="mb-3">
                        <label class="form-label fw-semibold">
                            Nombre del grupo
                        </label>

                        <div class="input-group">
                            <span class="input-group-text">
                                <i class="bi bi-people"></i>
                            </span>

                            <input
                                type="text"
                                class="form-control"
                                name="nombre"
                                placeholder="Ej. Tecnología de la Información"
                                maxlength="100"
                                required
                            >
                        </div>
                    </div>

                    <div class="mb-2">
                        <label class="form-label fw-semibold">
                            Descripción
                        </label>

                        <div class="input-group">
                            <span class="input-group-text">
                                <i class="bi bi-card-text"></i>
                            </span>

                            <textarea
                                class="form-control"
                                name="descripcion"
                                rows="4"
                                maxlength="255"
                                placeholder="Describe la función o responsabilidad del grupo."
                            ></textarea>
                        </div>
                    </div>
                </form>
                `;
            break;
        default:
            break;
    }
    modal_footer.innerHTML = botones;
    modal_cuerpo.innerHTML = html;
    modal_titulo.innerHTML = titulo
    modal.show();
}

const cerrar_modal = () => {
    modal.hide();
}


brn_cerrarsider.addEventListener('click', function (){
    cerrar_sider();
})

menu.addEventListener('click', function(){
    accion_menu();
})