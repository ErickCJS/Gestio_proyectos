let estado_sider = localStorage.getItem('estado_sider') ?? 1;
var sidebar = document.getElementById('sidebar');
var mainContent = document.getElementById('mainContent');
var menu = document.getElementById('btnToggleSidebar');
var brn_cerrarsider = document.getElementById('sidebarClose');
var el_modal = document.getElementById('projectModal');
var modal = new bootstrap.Modal(el_modal);
var modal_dialog = document.querySelector('#projectModal .modal-dialog');
const modal_titulo = document.getElementById('projectModalLabel');
const modal_cuerpo = document.getElementById('cuerpo_modal');
const modal_footer = document.getElementById('modal_footer');
let timeout_busqueda_personas = null;
let estado_integrantes_modal = {
    id_grupo: null,
    nombre: '',
    roles: [],
    personas: []
};

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

function escaparHtmlRiesgo(valor) {
    return String(valor ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function opcionRiesgo(actual, valor, texto) {
    return `<option value="${valor}" ${actual === valor ? 'selected' : ''}>${texto}</option>`;
}

function construirFormularioRiesgo(config = {}) {
    const formId = config.formId || 'frm_crearriesgo';
    const action = config.action || '/crear_riesgo';
    const nombre = escaparHtmlRiesgo(config.nombre || '');
    const descripcion = escaparHtmlRiesgo(config.descripcion || '');
    const impacto = config.impacto || 'INSIGNIFICANTE';
    const probabilidad = config.probabilidad || 'RARA';

    return `
        <form id="${formId}" method="post" action="${action}">
            <div class="row g-4 align-items-start">
                <div class="col-lg-6">
                    <div class="mb-3">
                        <label class="form-label modal-label">Nombre del riesgo</label>
                        <input type="text" name="nombre" class="form-control" value="${nombre}" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Descripción</label>
                        <textarea name="descripcion" rows="3" class="form-control">${descripcion}</textarea>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Impacto</label>
                        <select id="impacto" name="impacto" class="form-select" onchange="actualizarMapaRiesgo()">
                            ${opcionRiesgo(impacto, 'INSIGNIFICANTE', 'Insignificante')}
                            ${opcionRiesgo(impacto, 'MENOR', 'Menor')}
                            ${opcionRiesgo(impacto, 'MODERADO', 'Moderado')}
                            ${opcionRiesgo(impacto, 'MAYOR', 'Mayor')}
                            ${opcionRiesgo(impacto, 'CATASTROFICO', 'Catastrófico')}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Probabilidad</label>
                        <select id="probabilidad" name="probabilidad" class="form-select" onchange="actualizarMapaRiesgo()">
                            ${opcionRiesgo(probabilidad, 'RARA', 'Rara')}
                            ${opcionRiesgo(probabilidad, 'IMPROBABLE', 'Improbable')}
                            ${opcionRiesgo(probabilidad, 'POSIBLE', 'Posible')}
                            ${opcionRiesgo(probabilidad, 'PROBABLE', 'Probable')}
                            ${opcionRiesgo(probabilidad, 'CASI_SEGURO', 'Casi seguro')}
                        </select>
                    </div>
                    <div class="mt-4">
                        <label class="form-label modal-label">Nivel calculado</label>
                        <div id="nivelCalculado" class="badge fs-6">MUY BAJO</div>
                    </div>
                </div>
                <div class="col-lg-6 riesgo-modal-map-panel">
                    <div class="riesgo-modal-impact-title">Impacto</div>
                    <div class="riesgo-modal-matrix">
                        <div class="riesgo-modal-axis">Probabilidad</div>
                        <div class="riesgo-modal-matrix-content">
                            <div class="riesgo-modal-xlabels">
                                <div>1<br><span>Ins.</span></div>
                                <div>2<br><span>Men.</span></div>
                                <div>3<br><span>Mod.</span></div>
                                <div>4<br><span>May.</span></div>
                                <div>5<br><span>Cat.</span></div>
                            </div>
                            <div class="riesgo-modal-grid-row">
                                <div class="riesgo-modal-ylabels">
                                    <div>5<br><span>C.S.</span></div>
                                    <div>4<br><span>Prob.</span></div>
                                    <div>3<br><span>Pos.</span></div>
                                    <div>2<br><span>Imp.</span></div>
                                    <div>1<br><span>Rar.</span></div>
                                </div>
                                <div class="riesgo-modal-grid-wrap">
                                    <div id="mapaRiesgoModal" class="riesgo-modal-grid">
                                        ${crearMapaModal()}
                                    </div>
                                    <div id="marcadorModal" class="riesgo-modal-marker">R.I.</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="riesgo-modal-legend">
                        <span><i style="background:#d9ead3"></i>Muy bajo 1</span>
                        <span><i style="background:#22c55e"></i>Bajo 2-4</span>
                        <span><i style="background:#fbbf24"></i>Medio 5-9</span>
                        <span><i style="background:#f97316"></i>Alto 10-16</span>
                        <span><i style="background:#ef4444"></i>Extremo 17-25</span>
                    </div>
                </div>
            </div>
        </form>
    `;
}
const formatearPorcentajeControl = (valor) => {
    if (valor === undefined || valor === null || valor === '') return '-';
    const numero = Number(valor);
    return Number.isFinite(numero) ? `${numero}%` : '-';
}

const actualizarMaximosRiesgoControl = (select) => {
    if (!select) return;

    const opcion = select.selectedOptions?.[0];
    const probabilidad = opcion?.dataset?.maximoProbabilidad || '';
    const impacto = opcion?.dataset?.maximoImpacto || '';
    const salidaProbabilidad = document.getElementById('maximoRiesgoProbabilidad');
    const salidaImpacto = document.getElementById('maximoRiesgoImpacto');
    const salidaFormula = document.getElementById('maximoRiesgoFormula');
    const valorProbabilidad = Number(probabilidad);
    const valorImpacto = Number(impacto);

    if (salidaProbabilidad) salidaProbabilidad.textContent = formatearPorcentajeControl(probabilidad);
    if (salidaImpacto) salidaImpacto.textContent = formatearPorcentajeControl(impacto);
    if (salidaFormula) {
        salidaFormula.textContent = probabilidad !== '' && impacto !== '' && Number.isFinite(valorProbabilidad) && Number.isFinite(valorImpacto)
            ? `${valorProbabilidad} x ${valorImpacto} / 100 = ${(valorProbabilidad * valorImpacto) / 100}`
            : '-';
    }
}

const inicializarMaximosRiesgoControl = () => {
    const select = document.querySelector('[data-control-riesgo-select]');
    if (!select) return;

    select.addEventListener('change', () => actualizarMaximosRiesgoControl(select));
    actualizarMaximosRiesgoControl(select);
}
const mostrar_modal = (tipo, data = {}) => {
    var html = '';
    var titulo = "";
    var botones = "";
    var modalClass = 'modal-dialog modal-dialog-centered';

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

        case 'editar_grupo':
            titulo = `Editar Grupo #${String(data.id_grupo).padStart(3, '0')}`;
            botones = `
                <button type="button" class="btn btn-sm btn-secondary" onclick="cerrar_modal()">Cancelar</button>
                <button type="submit" class="btn btn-sm btn_primario" form="frm_editargrupo">
                    <i class="bi bi-floppy me-2"></i>
                    Guardar cambios
                </button>
            `;
            html = `
                <form id="frm_editargrupo" method="post" action="/grupo/${data.id_grupo}/editar">
                    <div class="mb-3">
                        <label class="form-label modal-label">Nombre del grupo</label>
                        <div class="input-group">
                            <span class="input-group-text"><i class="bi bi-people"></i></span>
                            <input type="text" class="form-control" name="nombre" value="${data.nombre ?? ''}" maxlength="100" required>
                        </div>
                    </div>
                    <div class="mb-2">
                        <label class="form-label modal-label">Descripción</label>
                        <div class="input-group">
                            <span class="input-group-text"><i class="bi bi-card-text"></i></span>
                            <textarea class="form-control" name="descripcion" rows="4" maxlength="255">${data.descripcion ?? ''}</textarea>
                        </div>
                    </div>
                </form>
            `;
            break;

        case 'integrantes_grupo': {
            titulo = `Integrantes del grupo #${String(data.id_grupo).padStart(3, '0')}`;
            modalClass = 'modal-dialog modal-dialog-centered modal-xl modal-integrantes';
            estado_integrantes_modal = {
                id_grupo: data.id_grupo,
                nombre: data.nombre ?? '',
                roles: [],
                personas: []
            };

            botones = `
                <button type="button" class="btn btn-sm btn-secondary" onclick="cerrar_modal()">Cerrar</button>
            `;
            html = `
                <div class="mb-3">
                    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
                        <div>
                            <div class="fw-semibold text-dark">${data.nombre ?? ''}</div>
                            <div class="text-secondary small">Gestiona los integrantes del grupo y su rol asignado.</div>
                        </div>
                        <button type="button" class="btn btn-sm btn_primario" onclick="asignar_integrante_grupo()">
                            <i class="bi bi-person-plus-fill me-2"></i>
                            Asignar
                        </button>
                    </div>
                </div>

                <div class="row g-2 mb-3">
                    <div class="col-12 col-lg-5">
                        <label class="form-label modal-label">Buscar persona</label>
                        <div class="input-group integrantes-search">
                            <span class="input-group-text"><i class="bi bi-search"></i></span>
                            <input id="buscadorPersonas" type="text" class="form-control" placeholder="Nombre o correo" oninput="programar_busqueda_personas()">
                            <button type="button" class="btn btn_primario" onclick="buscar_personas_grupo()">Buscar</button>
                        </div>
                    </div>
                    <div class="col-12 col-lg-4">
                        <label class="form-label modal-label">Persona encontrada</label>
                        <select id="selectPersonasBuscadas" class="form-select">
                            <option value="">Busque una persona primero</option>
                        </select>
                    </div>
                    <div class="col-12 col-lg-3">
                        <label class="form-label modal-label">Rol en el grupo</label>
                        <select id="selectRolGrupo" class="form-select">
                            <option value="">Cargando roles...</option>
                        </select>
                    </div>
                </div>

                <div class="table-responsive tabla-wrap tabla-integrantes-wrap mt-0">
                    <table class="table table-hover table-sm align-middle tabla-compacta tabla-integrantes w-100 mb-0">
                        <thead>
                            <tr>
                                <th>Integrante</th>
                                <th>Correo</th>
                                <th>Rol</th>
                                <th class="text-center">Acciones</th>
                            </tr>
                        </thead>
                        <tbody id="tablaIntegrantesGrupoBody">
                            <tr>
                                <td colspan="4" class="text-center text-secondary py-4">Cargando integrantes...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            `;
            break;
        }

        case 'nriesgo': {
            modalClass = 'modal-dialog modal-dialog-centered modal-lg modal-riesgo';
            titulo = "Registrar Riesgo";
            botones = `
                <button type="button" class="btn btn-sm btn-secondary" onclick="cerrar_modal()">
                    Cancelar
                </button>
                <button type="submit" class="btn btn-sm btn_primario" form="frm_crearriesgo">
                    <i class="bi bi-floppy me-2"></i>
                    Guardar riesgo
                </button>
            `;
            html = construirFormularioRiesgo({
                formId: 'frm_crearriesgo',
                action: '/crear_riesgo'
            });
            break;
        }

        case 'editar_riesgo': {
            modalClass = 'modal-dialog modal-dialog-centered modal-lg modal-riesgo';
            titulo = "Editar Riesgo";
            botones = `
                <button type="button" class="btn btn-sm btn-secondary" onclick="cerrar_modal()">
                    Cancelar
                </button>
                <button type="submit" class="btn btn-sm btn_primario" form="frm_editarriesgo">
                    <i class="bi bi-floppy me-2"></i>
                    Guardar cambios
                </button>
            `;
            html = construirFormularioRiesgo({
                formId: 'frm_editarriesgo',
                action: `/riesgo/${data.id_riesgo}/editar`,
                nombre: data.nombre,
                descripcion: data.descripcion,
                impacto: data.impacto,
                probabilidad: data.probabilidad
            });
            break;
        }

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

        case 'editar_proceso': {
            titulo = `Editar Proceso #${String(data.id_proceso).padStart(3, '0')}`;
            const gruposEd = (window.catalogosProcesos && window.catalogosProcesos.grupos) ? window.catalogosProcesos.grupos : [];
            const opcionesGruposEd = gruposEd.map(item => `<option value="${item.id_grupo}" ${String(item.id_grupo) === String(data.id_grupo) ? 'selected' : ''}>${item.nombre}</option>`).join('');
            botones = `
                <button type="button" class="btn btn-sm btn-secondary" onclick="cerrar_modal()">Cancelar</button>
                <button type="submit" class="btn btn-sm btn_primario" form="frm_editarproceso">
                    <i class="bi bi-floppy me-2"></i>
                    Guardar cambios
                </button>
            `;
            html = `
                <form id="frm_editarproceso" method="post" action="/procesos/${data.id_proceso}/editar">
                    <div class="mb-3">
                        <label class="form-label modal-label">Nombre del proceso</label>
                        <input type="text" class="form-control" name="nombre" value="${data.nombre ?? ''}" maxlength="150" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Descripción</label>
                        <textarea class="form-control" name="descripcion" rows="3" maxlength="255">${data.descripcion ?? ''}</textarea>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Grupo responsable</label>
                        <select class="form-select" name="id_grupo" required>
                            <option value="">Seleccione un grupo</option>
                            ${opcionesGruposEd}
                        </select>
                    </div>
                </form>
            `;
            break;
        }

        case 'ncontrol': {
            titulo = "Crear Control";
            const catalogos = window.catalogosControles || {};
            const riesgos = Array.isArray(catalogos.riesgos) ? catalogos.riesgos : [];
            const opcionesRiesgos = riesgos.map(item => `<option value="${item.id_riesgo}" data-maximo-probabilidad="${item.maximo_baja_probabilidad ?? 100}" data-maximo-impacto="${item.maximo_baja_impacto ?? 100}">${item.nombre}</option>`).join('');
            botones = `
                <button type="button" class="btn btn-sm btn-secondary" onclick="cerrar_modal()">Cancelar</button>
                <button type="submit" class="btn btn-sm btn_primario" form="frm_crearcontrol">
                    <i class="bi bi-floppy me-2"></i>
                    Guardar control
                </button>
            `;
            html = `
                <form id="frm_crearcontrol" method="post" action="/crear_control">
                    <div class="mb-3">
                        <label class="form-label modal-label">Riesgo asociado</label>
                        <select class="form-select" name="id_riesgo" data-control-riesgo-select required>
                            <option value="">Seleccione un riesgo</option>
                            ${opcionesRiesgos}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Nombre del control</label>
                        <input type="text" class="form-control" name="nombre" placeholder="Ej. Revisión de accesos" maxlength="150" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Descripción</label>
                        <textarea class="form-control" name="descripcion" rows="3" maxlength="255" placeholder="Describe cómo funciona el control."></textarea>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Tipo de control</label>
                        <select class="form-select" name="tipo" required>
                            <option value="Preventivo">Preventivo</option>
                            <option value="Detectivo">Detectivo</option>
                            <option value="Correctivo">Correctivo</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Solidez del control</label>
                        <select class="form-select" name="solidez_control" required>
                            <option value="Muy baja">Muy baja</option>
                            <option value="Baja">Baja</option>
                            <option value="Media" selected>Media</option>
                            <option value="Alta">Alta</option>
                            <option value="Muy alta">Muy alta</option>
                        </select>
                    </div>
                    <div class="alert alert-light border mb-3">
                        <div class="fw-semibold mb-2">Máximo heredado del riesgo</div>
                        <div class="d-flex flex-wrap gap-2">
                            <span class="badge bg-secondary">Probabilidad <strong id="maximoRiesgoProbabilidad">-</strong></span>
                            <span class="badge bg-secondary">Impacto <strong id="maximoRiesgoImpacto">-</strong></span>
                        </div>
                        <small class="text-secondary d-block mt-2" id="maximoRiesgoFormula">-</small>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Mitigación probabilidad (%)</label>
                        <div class="d-flex align-items-center gap-2">
                            <input type="range" class="form-range flex-grow-1" name="mitigacion_probabilidad" min="0" max="100" value="0" oninput="this.nextElementSibling.textContent = this.value + '%';">
                            <span class="badge bg-secondary">0%</span>
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Mitigación impacto (%)</label>
                        <div class="d-flex align-items-center gap-2">
                            <input type="range" class="form-range flex-grow-1" name="mitigacion_impacto" min="0" max="100" value="0" oninput="this.nextElementSibling.textContent = this.value + '%';">
                            <span class="badge bg-secondary">0%</span>
                        </div>
                    </div>
                </form>
            `;
            break;
        }

        case 'editar_control': {
            titulo = `Editar Control #${String(data.id_control).padStart(3, '0')}`;
            const catalogosEd = window.catalogosControles || {};
            const riesgosEd = Array.isArray(catalogosEd.riesgos) ? catalogosEd.riesgos : [];
            const opcionesRiesgosEd = riesgosEd.map(item => `<option value="${item.id_riesgo}" data-maximo-probabilidad="${item.maximo_baja_probabilidad ?? 100}" data-maximo-impacto="${item.maximo_baja_impacto ?? 100}" ${String(item.id_riesgo) === String(data.id_riesgo) ? 'selected' : ''}>${item.nombre}</option>`).join('');
            botones = `
                <button type="button" class="btn btn-sm btn-secondary" onclick="cerrar_modal()">Cancelar</button>
                <button type="submit" class="btn btn-sm btn_primario" form="frm_editarcontrol">
                    <i class="bi bi-floppy me-2"></i>
                    Guardar cambios
                </button>
            `;
            html = `
                <form id="frm_editarcontrol" method="post" action="/control/${data.id_control}/editar">
                    <div class="mb-3">
                        <label class="form-label modal-label">Riesgo asociado</label>
                        <select class="form-select" name="id_riesgo" data-control-riesgo-select required>
                            <option value="">Seleccione un riesgo</option>
                            ${opcionesRiesgosEd}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Nombre del control</label>
                        <input type="text" class="form-control" name="nombre" value="${data.nombre ?? ''}" maxlength="150" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Descripción</label>
                        <textarea class="form-control" name="descripcion" rows="3" maxlength="255">${data.descripcion ?? ''}</textarea>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Tipo de control</label>
                        <select class="form-select" name="tipo" required>
                            <option value="Preventivo" ${data.tipo === 'Preventivo' ? 'selected' : ''}>Preventivo</option>
                            <option value="Detectivo" ${data.tipo === 'Detectivo' ? 'selected' : ''}>Detectivo</option>
                            <option value="Correctivo" ${data.tipo === 'Correctivo' ? 'selected' : ''}>Correctivo</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Solidez del control</label>
                        <select class="form-select" name="solidez_control" required>
                            <option value="Muy baja" ${data.solidez_control === 'Muy baja' ? 'selected' : ''}>Muy baja</option>
                            <option value="Baja" ${data.solidez_control === 'Baja' ? 'selected' : ''}>Baja</option>
                            <option value="Media" ${data.solidez_control === 'Media' ? 'selected' : ''}>Media</option>
                            <option value="Alta" ${data.solidez_control === 'Alta' ? 'selected' : ''}>Alta</option>
                            <option value="Muy alta" ${data.solidez_control === 'Muy alta' ? 'selected' : ''}>Muy alta</option>
                        </select>
                    </div>
                    <div class="alert alert-light border mb-3">
                        <div class="fw-semibold mb-2">Máximo heredado del riesgo</div>
                        <div class="d-flex flex-wrap gap-2">
                            <span class="badge bg-secondary">Probabilidad <strong id="maximoRiesgoProbabilidad">-</strong></span>
                            <span class="badge bg-secondary">Impacto <strong id="maximoRiesgoImpacto">-</strong></span>
                        </div>
                        <small class="text-secondary d-block mt-2" id="maximoRiesgoFormula">-</small>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Mitigación probabilidad (%)</label>
                        <div class="d-flex align-items-center gap-2">
                            <input type="range" class="form-range flex-grow-1" name="mitigacion_probabilidad" min="0" max="100" value="${data.mitigacion_probabilidad ?? 0}" oninput="this.nextElementSibling.textContent = this.value + '%';">
                            <span class="badge bg-secondary">${data.mitigacion_probabilidad ?? 0}%</span>
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label modal-label">Mitigación impacto (%)</label>
                        <div class="d-flex align-items-center gap-2">
                            <input type="range" class="form-range flex-grow-1" name="mitigacion_impacto" min="0" max="100" value="${data.mitigacion_impacto ?? 0}" oninput="this.nextElementSibling.textContent = this.value + '%';">
                            <span class="badge bg-secondary">${data.mitigacion_impacto ?? 0}%</span>
                        </div>
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
                <div class="mb-2">
                    <label class="form-label modal-label">Integrantes</label>
                    <div class="table-responsive tabla-wrap tabla-vista-grupo mt-0">
                        <table class="table table-hover table-sm align-middle tabla-compacta tabla-integrantes w-100 mb-0">
                            <thead>
                                <tr>
                                    <th>Integrante</th>
                                    <th>Correo</th>
                                    <th>Rol</th>
                                    <th>Fecha ingreso</th>
                                </tr>
                            </thead>
                            <tbody id="tablaVistaGrupoBody">
                                <tr>
                                    <td colspan="4" class="text-center text-secondary py-4">Cargando integrantes...</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
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

        case 'ver_control':
            titulo = `Control #${String(data.id_control).padStart(3, '0')}`;
            botones = `
                <button type="button" class="btn btn-sm btn-secondary" onclick="cerrar_modal()">Cerrar</button>
            `;
            html = `
                <div class="mb-3">
                    <label class="form-label modal-label">Código</label>
                    <div class="modal-readonly-field">CTL-${String(data.id_control).padStart(3, '0')}</div>
                </div>
                <div class="mb-3">
                    <label class="form-label modal-label">Riesgo asociado</label>
                    <div class="modal-readonly-field">${data.riesgo_nombre ?? ''}</div>
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
                    <label class="form-label modal-label">Tipo</label>
                    <div class="modal-readonly-field">${data.tipo ?? ''}</div>
                </div>
            `;
            break;

        default:
            break;
    }

    if (modal_dialog) {
        modal_dialog.className = modalClass;
    }
    modal_footer.innerHTML = botones;
    modal_cuerpo.innerHTML = html;
    modal_titulo.innerHTML = titulo;
    inicializarMaximosRiesgoControl();

    const debeActualizarMapa = Boolean(
        document.getElementById('impacto') &&
        document.getElementById('probabilidad') &&
        document.getElementById('mapaRiesgoModal')
    );
    const repintarMapaRiesgo = () => {
        if (!debeActualizarMapa) return;
        actualizarMapaRiesgo();
        requestAnimationFrame(actualizarMapaRiesgo);
    };

    if (debeActualizarMapa) {
        el_modal.addEventListener('shown.bs.modal', repintarMapaRiesgo, { once: true });
    }
    modal.show();
    if (debeActualizarMapa) {
        setTimeout(repintarMapaRiesgo, 380);
    }
}

const cerrar_modal = () => {
    modal.hide();
}

const normalizar_texto = (valor) => (valor ?? '').toString().trim();

const mostrar_mensaje_modal = (texto, tipo = 'success') => {
    const contenedor = document.getElementById('alertasFlotantes');

    if (!contenedor) {
        alert(texto);
        return;
    }

    const alerta = document.createElement('div');
    const icono = tipo === 'success'
        ? 'bi-check-circle-fill'
        : tipo === 'warning'
            ? 'bi-exclamation-triangle-fill'
            : 'bi-x-circle-fill';

    alerta.className = `alert alert-${tipo} alert-dismissible fade show alerta-flotante mb-0`;
    alerta.setAttribute('role', 'alert');
    alerta.innerHTML = `
        <div class="d-flex align-items-start gap-2">
            <i class="bi ${icono} alerta-flotante-icon"></i>
            <div class="flex-grow-1">${texto}</div>
            <button type="button" class="btn-close btn-close-sm" data-bs-dismiss="alert" aria-label="Cerrar"></button>
        </div>
    `;

    contenedor.appendChild(alerta);

    window.setTimeout(() => {
        alerta.classList.remove('show');
        alerta.classList.add('hide');
        window.setTimeout(() => alerta.remove(), 200);
    }, 2500);
}

const renderizar_roles_modal = () => {
    const selectRoles = document.getElementById('selectRolGrupo');
    const rolesTxt = document.getElementById('rolesCargadosTxt');

    if (!selectRoles) {
        return;
    }

    if (!estado_integrantes_modal.roles.length) {
        selectRoles.innerHTML = '<option value="">No hay roles disponibles</option>';
        if (rolesTxt) {
            rolesTxt.textContent = '0';
        }
        return;
    }

    if (rolesTxt) {
        rolesTxt.textContent = String(estado_integrantes_modal.roles.length);
    }

    selectRoles.innerHTML = `
        <option value="">Seleccione un rol</option>
        ${estado_integrantes_modal.roles.map((rol) => `
            <option value="${rol.id_rol}">${rol.nombre}</option>
        `).join('')}
    `;
}

const renderizar_integrantes_modal = (integrantes) => {
    const tbody = document.getElementById('tablaIntegrantesGrupoBody');
    const integrantesTxt = document.getElementById('integrantesActivosTxt');

    if (!tbody) {
        return;
    }

    actualizar_contador_integrantes_tabla(integrantes.length);

    if (integrantesTxt) {
        integrantesTxt.textContent = String(integrantes.length);
    }

    if (!integrantes.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-secondary py-4">
                    No hay integrantes asignados.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = integrantes.map((integrante) => `
        <tr>
            <td>
                <div class="d-flex align-items-center gap-2">
                    <div class="avatar-mini">
                        ${(integrante.nombres_completo ?? '').split(' ').filter(Boolean).slice(0, 2).map((parte) => parte.charAt(0)).join('').toUpperCase()}
                    </div>
                    <div class="min-w-0">
                        <div class="fw-semibold text-dark text-truncate">${integrante.nombres_completo ?? ''}</div>
                    </div>
                </div>
            </td>
            <td class="text-secondary">${integrante.correo ?? ''}</td>
            <td>
                <span class="badge badge-soft-role">${integrante.rol_nombre ?? ''}</span>
            </td>
            <td class="text-center">
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="quitar_integrante_grupo(${integrante.id_usuario_grupo})">
                    <i class="bi bi-person-dash me-1"></i>
                    Quitar
                </button>
            </td>
        </tr>
    `).join('');
}

const renderizar_integrantes_sin_acciones = (integrantes, tbodyId) => {
    const tbody = document.getElementById(tbodyId);

    if (!tbody) {
        return;
    }

    if (!integrantes.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-secondary py-4">
                    No hay integrantes asignados.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = integrantes.map((integrante) => `
        <tr>
            <td>
                <div class="d-flex align-items-center gap-2">
                    <div class="avatar-mini">
                        ${(integrante.nombres_completo ?? '').split(' ').filter(Boolean).slice(0, 2).map((parte) => parte.charAt(0)).join('').toUpperCase()}
                    </div>
                    <div class="min-w-0">
                        <div class="fw-semibold text-dark text-truncate">${integrante.nombres_completo ?? ''}</div>
                    </div>
                </div>
            </td>
            <td class="text-secondary">${integrante.correo ?? ''}</td>
            <td><span class="badge badge-soft-role">${integrante.rol_nombre ?? ''}</span></td>
            <td class="text-secondary">${integrante.fecha_ingreso ?? ''}</td>
        </tr>
    `).join('');
}

const actualizar_contador_integrantes_tabla = (total) => {
    if (!estado_integrantes_modal.id_grupo) {
        return;
    }

    const contador = document.getElementById(`count-integrantes-${estado_integrantes_modal.id_grupo}`);
    if (contador) {
        contador.textContent = String(total);
    }
}

const cargar_roles_grupo = async () => {
    try {
        const respuesta = await fetch('/roles/listar');

        if (!respuesta.ok) {
            throw new Error('No se pudieron cargar los roles');
        }

        estado_integrantes_modal.roles = await respuesta.json();
        renderizar_roles_modal();
    } catch (error) {
        console.error(error);
        const selectRoles = document.getElementById('selectRolGrupo');
        if (selectRoles) {
            selectRoles.innerHTML = '<option value="">Error al cargar roles</option>';
        }
    }
}

const cargar_integrantes_grupo = async () => {
    const tbody = document.getElementById('tablaIntegrantesGrupoBody');

    try {
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-secondary py-4">Cargando integrantes...</td></tr>';
        }

        const respuesta = await fetch(`/grupo/${estado_integrantes_modal.id_grupo}/integrantes`);

        if (!respuesta.ok) {
            throw new Error('No se pudieron cargar los integrantes');
        }

        const integrantes = await respuesta.json();
        renderizar_integrantes_modal(integrantes);
        actualizar_contador_integrantes_tabla(integrantes.length);
    } catch (error) {
        console.error(error);
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger py-4">No se pudieron cargar los integrantes.</td></tr>';
        }
    }
}

const buscar_personas_grupo = async () => {
    const input = document.getElementById('buscadorPersonas');
    const select = document.getElementById('selectPersonasBuscadas');
    const termino = normalizar_texto(input?.value);

    if (!select) {
        return;
    }

    if (termino === '') {
        select.innerHTML = '<option value="">Escriba para buscar personas</option>';
        return;
    }

    select.innerHTML = '<option value="">Buscando...</option>';

    try {
        const respuesta = await fetch(`/personas/buscar?q=${encodeURIComponent(termino)}`);

        if (!respuesta.ok) {
            throw new Error('No se pudo buscar personas');
        }

        const personas = await respuesta.json();
        estado_integrantes_modal.personas = personas;

        if (!personas.length) {
            select.innerHTML = '<option value="">No se encontraron resultados</option>';
            return;
        }

        select.innerHTML = `
            <option value="">Seleccione una persona</option>
            ${personas.map((persona) => `
                <option value="${persona.correo}">${persona.nombres_completo} - ${persona.correo}</option>
            `).join('')}
        `;
    } catch (error) {
        select.innerHTML = '<option value="">Error al buscar personas</option>';
        console.error(error);
    }
}

const programar_busqueda_personas = () => {
    if (timeout_busqueda_personas) {
        clearTimeout(timeout_busqueda_personas);
    }

    timeout_busqueda_personas = setTimeout(() => {
        buscar_personas_grupo();
    }, 300);
}

const asignar_integrante_grupo = async () => {
    const selectPersona = document.getElementById('selectPersonasBuscadas');
    const selectRol = document.getElementById('selectRolGrupo');
    const correo = normalizar_texto(selectPersona?.value);
    const idRol = normalizar_texto(selectRol?.value);

    if (!correo || !idRol) {
        mostrar_mensaje_modal('Seleccione una persona y un rol.', 'warning');
        return;
    }

    try {
        const respuesta = await fetch(`/grupo/${estado_integrantes_modal.id_grupo}/integrantes/asignar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                correo,
                id_rol: idRol
            })
        });

        if (!respuesta.ok) {
            const data = await respuesta.json().catch(() => null);
            throw new Error(data?.detail || 'No se pudo asignar la persona');
        }

        await cargar_integrantes_grupo();
        if (selectPersona) {
            selectPersona.value = '';
        }
        if (selectRol) {
            selectRol.value = '';
        }
        mostrar_mensaje_modal('Integrante agregado correctamente.', 'success');
    } catch (error) {
        mostrar_mensaje_modal(error.message, 'danger');
    }
}

const quitar_integrante_grupo = async (id_usuario_grupo) => {
    if (!confirm('¿Seguro que deseas quitar este integrante del grupo?')) {
        return;
    }

    try {
        const respuesta = await fetch(`/grupo/${estado_integrantes_modal.id_grupo}/integrantes/${id_usuario_grupo}/quitar`, {
            method: 'POST'
        });

        if (!respuesta.ok) {
            const data = await respuesta.json().catch(() => null);
            throw new Error(data?.detail || 'No se pudo quitar al integrante');
        }

        await cargar_integrantes_grupo();
        mostrar_mensaje_modal('Integrante eliminado correctamente.', 'success');
    } catch (error) {
        mostrar_mensaje_modal(error.message, 'danger');
    }
}

const cargar_integrantes_vista_grupo = async (id_grupo) => {
    const tbody = document.getElementById('tablaVistaGrupoBody');

    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-secondary py-4">Cargando integrantes...</td></tr>';
    }

    try {
        const respuesta = await fetch(`/grupo/${id_grupo}/integrantes`);

        if (!respuesta.ok) {
            throw new Error('No se pudieron cargar los integrantes');
        }

        const integrantes = await respuesta.json();
        renderizar_integrantes_sin_acciones(integrantes, 'tablaVistaGrupoBody');
    } catch (error) {
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger py-4">No se pudieron cargar los integrantes.</td></tr>';
        }
    }
}

const ver_grupo = async (id_grupo, nombre, descripcion) => {
    mostrar_modal('ver_grupo', {
        id_grupo,
        nombre,
        descripcion,
    });
    await cargar_integrantes_vista_grupo(id_grupo);
}

const ver_grupo_desde_btn = async (btn) => {
    await ver_grupo(
        btn.dataset.idGrupo,
        btn.dataset.nombreGrupo,
        btn.dataset.descripcionGrupo || ''
    );
}

const ver_proceso = (id_proceso, nombre, descripcion, grupo_nombre) => {
    mostrar_modal('ver_proceso', {
        id_proceso,
        nombre,
        descripcion,
        grupo_nombre
    });
}

const ver_control = (id_control, nombre, descripcion, tipo, riesgo_nombre, estado) => {
    mostrar_modal('ver_control', {
        id_control,
        nombre,
        descripcion,
        tipo,
        riesgo_nombre,
        estado
    });
}

const mapaControlEfectos = {
    'No afecta': 0,
    'Baja': 1,
    'Media': 2,
    'Alta': 3,
    'Muy Alta': 4
};

const seleccionarFilaControl = (fila) => {
    document.querySelectorAll('.fila-control').forEach((elemento) => {
        elemento.classList.remove('table-active');
    });
    if (fila) {
        fila.classList.add('table-active');
    }
}

const mostrarDetalleControl = (
    nombre,
    codigo,
    descripcion,
    tipo,
    solidez_control,
    maximo_baja_probabilidad,
    maximo_baja_impacto,
    mitigacion_probabilidad,
    mitigacion_impacto,
    riesgo_nombre,
    estado
) => {
    const mapeoEstado = {
        Activo: 'Activo',
        Inactivo: 'Inactivo'
    };

    const detalleNombre = document.getElementById('detalleControlNombre');
    const detalleCodigo = document.getElementById('detalleControlCodigo');
    const detalleDescripcion = document.getElementById('detalleControlDescripcion');
    const detalleTipo = document.getElementById('detalleControlTipo');
    const detalleSolidez = document.getElementById('detalleControlSolidez');
    const detalleMaximoProbabilidad = document.getElementById('detalleControlMaximoProbabilidad');
    const detalleMaximoImpacto = document.getElementById('detalleControlMaximoImpacto');
    const detalleMitigacionProbabilidad = document.getElementById('detalleControlMitigacionProbabilidad');
    const detalleMitigacionImpacto = document.getElementById('detalleControlMitigacionImpacto');
    const detalleRiesgo = document.getElementById('detalleControlRiesgo');
    const detalleEstado = document.getElementById('detalleControlEstado');

    if (detalleNombre) detalleNombre.textContent = nombre || 'Control';
    if (detalleCodigo) detalleCodigo.textContent = codigo || '-';
    if (detalleDescripcion) detalleDescripcion.textContent = descripcion || '-';
    if (detalleTipo) detalleTipo.textContent = tipo || '-';
    if (detalleSolidez) detalleSolidez.textContent = solidez_control || '-';
    if (detalleMaximoProbabilidad) detalleMaximoProbabilidad.textContent = `${maximo_baja_probabilidad}%`;
    if (detalleMaximoImpacto) detalleMaximoImpacto.textContent = `${maximo_baja_impacto}%`;
    if (detalleMitigacionProbabilidad) detalleMitigacionProbabilidad.textContent = `${mitigacion_probabilidad}%`;
    if (detalleMitigacionImpacto) detalleMitigacionImpacto.textContent = `${mitigacion_impacto}%`;
    if (detalleRiesgo) detalleRiesgo.textContent = riesgo_nombre || '-';
    if (detalleEstado) detalleEstado.textContent = mapeoEstado[estado] || estado || '-';
}

window.seleccionarFilaControl = seleccionarFilaControl;
window.mostrarDetalleControl = mostrarDetalleControl;

const abrir_integrantes_grupo = async (id_grupo, nombre) => {
    mostrar_modal('integrantes_grupo', {
        id_grupo,
        nombre
    });
    await cargar_roles_grupo();
    await cargar_integrantes_grupo();
}

const abrir_integrantes_grupo_desde_btn = (btn) => {
    abrir_integrantes_grupo(
        btn.dataset.idGrupo,
        btn.dataset.nombreGrupo
    );
}

const abrir_editar_grupo = (btn) => {
    mostrar_modal('editar_grupo', {
        id_grupo: btn.dataset.idGrupo,
        nombre: btn.dataset.nombre || btn.dataset.nombreGrupo || '',
        descripcion: btn.dataset.descripcion || ''
    });
}

const abrir_editar_proceso = (btn) => {
    mostrar_modal('editar_proceso', {
        id_proceso: btn.dataset.idProceso || btn.dataset.id_proceso || btn.dataset.id_proceso,
        nombre: btn.dataset.nombre || '',
        descripcion: btn.dataset.descripcion || '',
        id_grupo: btn.dataset.idGrupo || btn.dataset.id_grupo || ''
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


const coloresMatrizRiesgo = [
    ['#fbbf24','#f97316','#f97316','#ef4444','#ef4444'],
    ['#22c55e','#fbbf24','#f97316','#f97316','#ef4444'],
    ['#22c55e','#fbbf24','#fbbf24','#f97316','#f97316'],
    ['#22c55e','#22c55e','#fbbf24','#fbbf24','#f97316'],
    ['#d9ead3','#22c55e','#22c55e','#22c55e','#fbbf24']
];

const valoresImpactoRiesgo = {
    INSIGNIFICANTE:1, MENOR:2, MODERADO:3, MAYOR:4, CATASTROFICO:5
};

const valoresProbabilidadRiesgo = {
    RARA:1, IMPROBABLE:2, POSIBLE:3, PROBABLE:4, CASI_SEGURO:5
};

const posicionesImpactoRiesgo = {
    INSIGNIFICANTE:0, MENOR:1, MODERADO:2, MAYOR:3, CATASTROFICO:4
};

const posicionesProbabilidadRiesgo = {
    RARA:4, IMPROBABLE:3, POSIBLE:2, PROBABLE:1, CASI_SEGURO:0
};

function obtenerPuntajeRiesgo(impacto, probabilidad) {
    return valoresImpactoRiesgo[impacto] * valoresProbabilidadRiesgo[probabilidad];
}

function crearMapaModal() {
    let html = '';
    for (let fila = 0; fila < 5; fila++) {
        for (let columna = 0; columna < 5; columna++) {
            const color = coloresMatrizRiesgo[fila][columna];
            const textoOscuro = color === '#d9ead3' || color === '#fbbf24';
            html += '<div class="riesgo-modal-cell" style="background:' + color + ';color:' + (textoOscuro ? '#111827' : '#ffffff') + ';"></div>';
        }
    }
    return html;
}

function obtenerColorRiesgoMapa(impacto, probabilidad) {
    const x = posicionesImpactoRiesgo[impacto];
    const y = posicionesProbabilidadRiesgo[probabilidad];
    if (x === undefined || y === undefined) {
        return null;
    }
    return coloresMatrizRiesgo[y][x];
}

function calcularNivelRiesgo(impacto, probabilidad) {
    const total = obtenerPuntajeRiesgo(impacto, probabilidad);

    if(total === 1){
        return 'MUY BAJO';
    }
    if(total <= 4){
        return 'BAJO';
    }
    if(total <= 9){
        return 'MEDIO';
    }
    if(total <= 16){
        return 'ALTO';
    }
    return 'EXTREMO';
}

function obtenerColorNivelRiesgo(nivel) {
    const colores = {
        'MUY BAJO': '#d9ead3',
        BAJO: '#22c55e',
        MEDIO: '#fbbf24',
        ALTO: '#f97316',
        EXTREMO: '#ef4444'
    };
    return colores[nivel] || null;
}
function actualizarMapaRiesgo() {
    const impacto = document.getElementById("impacto").value;
    const probabilidad = document.getElementById("probabilidad").value;
    moverMarcadorModal(
        impacto,
        probabilidad
    );
    calcularNivelModal(
        impacto,
        probabilidad
    );
}

function moverMarcadorModal(
    impacto,
    probabilidad
) {
    const colorMapa = obtenerColorRiesgoMapa(impacto, probabilidad);
    if (!colorMapa) {
        return;
    }

    const marcador = document.getElementById('marcadorModal');

    if(!marcador)
        return;

    const impactos = {
        INSIGNIFICANTE:0, MENOR:1, MODERADO:2, MAYOR:3, CATASTROFICO:4
    };
    const probabilidades = {
        RARA:4, IMPROBABLE:3, POSIBLE:2, PROBABLE:1, CASI_SEGURO:0
    };
    const x = impactos[impacto];
    const y = probabilidades[probabilidad];
    const celda = marcador.previousElementSibling?.children?.[y * 5 + x];
    const colorCelda = celda ? getComputedStyle(celda).backgroundColor : colorMapa;
    if (celda) {
        marcador.style.left = celda.offsetLeft + 'px';
        marcador.style.top = celda.offsetTop + 'px';
        marcador.style.width = celda.offsetWidth + 'px';
        marcador.style.height = celda.offsetHeight + 'px';
    }
    marcador.style.background = colorCelda;
    marcador.style.color = (colorMapa === '#d9ead3' || colorMapa === '#fbbf24') ? '#111827' : '#ffffff';

}

function calcularNivelModal(
    impacto,
    probabilidad
) {
    const badge =
        document.getElementById('nivelCalculado');
    if(!badge)
        return;

    const nivel = calcularNivelRiesgo(impacto, probabilidad);
    const colorMapa = obtenerColorRiesgoMapa(impacto, probabilidad);
    const marcador = document.getElementById('marcadorModal');
    const impactos = {
        INSIGNIFICANTE:0, MENOR:1, MODERADO:2, MAYOR:3, CATASTROFICO:4
    };
    const probabilidades = {
        RARA:4, IMPROBABLE:3, POSIBLE:2, PROBABLE:1, CASI_SEGURO:0
    };
    const x = impactos[impacto];
    const y = probabilidades[probabilidad];
    const celda = marcador?.previousElementSibling?.children?.[y * 5 + x];
    const colorCelda = celda ? getComputedStyle(celda).backgroundColor : colorMapa;

    badge.className = 'badge fs-6';
    badge.innerHTML = nivel;
    badge.style.background = colorCelda || '';
    badge.style.borderColor = colorCelda || '';
    badge.style.color = (colorMapa === '#d9ead3' || colorMapa === '#fbbf24') ? '#111827' : '#ffffff';
}
const eliminarControl = async (id_control) => {
    if (!confirm('¿Seguro que deseas eliminar este control?')) {
        return;
    }

    try {
        const respuesta = await fetch(`/control/${id_control}/eliminar`, {
            method: 'POST'
        });

        if (!respuesta.ok) {
            throw new Error('No se pudo eliminar el control');
        }

        window.location.reload();
    } catch (error) {
        alert(error.message);
    }
}

function abrirEditarRiesgo(boton) {
    mostrar_modal('editar_riesgo', {
        id_riesgo: boton.dataset.idRiesgo,
        nombre: boton.dataset.nombre || '',
        descripcion: boton.dataset.descripcion || '',
        impacto: boton.dataset.impacto || 'INSIGNIFICANTE',
        probabilidad: boton.dataset.probabilidad || 'RARA'
    });
}
async function eliminarRiesgo(id) {
    event.stopPropagation();
    if (!confirm("¿Desea eliminar este riesgo?")) {
        return;
    }
    try {
        const respuesta = await fetch(`/riesgo/${id}/eliminar`, {
            method: "POST"
        });
        if (!respuesta.ok) {
            throw new Error("No se pudo eliminar el riesgo.");
        }
        location.reload();
    } catch (error) {
        alert(error.message);
    }
}

function construirItemProcesoDisponible(idRiesgo, proceso) {
    const nombre = escaparHtmlRiesgo(proceso.nombre || 'Proceso');
    const filtro = escaparHtmlRiesgo(String(proceso.nombre || '').toLowerCase());
    return `
        <div class="list-group-item d-flex justify-content-between align-items-center gap-2" data-nombre="${filtro}">
            <span class="text-truncate">${nombre}</span>
            <button type="button" class="btn btn-sm btn-success" onclick="agregarProceso(${idRiesgo}, ${proceso.id_proceso})" title="Asociar proceso">
                <i class="bi bi-plus"></i>
            </button>
        </div>
    `;
}

function construirItemProcesoAsociado(idRiesgo, proceso) {
    const nombre = escaparHtmlRiesgo(proceso.nombre || 'Proceso');
    return `
        <div class="list-group-item d-flex justify-content-between align-items-center gap-2">
            <span class="text-truncate">${nombre}</span>
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="quitarProceso(${idRiesgo}, ${proceso.id_proceso})" title="Quitar proceso">
                <i class="bi bi-x-lg"></i>
            </button>
        </div>
    `;
}

function mostrarCuerpoProcesos(idRiesgo) {
    modal_dialog.className = 'modal-dialog modal-dialog-centered modal-lg modal-procesos-riesgo';
    modal_titulo.innerHTML = 'Procesos asociados';
    modal_cuerpo.innerHTML = `
        <div class="procesos-riesgo-modal">
            <div class="procesos-riesgo-hero">
                <div>
                    <span class="procesos-riesgo-kicker">Relación del riesgo</span>
                    <strong>Conecta este riesgo con los procesos donde impacta</strong>
                    <small>Asocia o retira procesos sin salir de la tabla.</small>
                </div>
                <div id="procesosModalEstado" class="procesos-riesgo-status">
                    <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                    <span>Cargando...</span>
                </div>
            </div>

            <div class="row g-3">
                <div class="col-12 col-lg-6">
                    <section class="procesos-riesgo-card">
                        <div class="procesos-riesgo-heading">
                            <span><i class="bi bi-search"></i></span>
                            <div>
                                <strong>Procesos disponibles</strong>
                                <small>Busca y agrega los que correspondan.</small>
                            </div>
                        </div>
                        <div class="input-group mb-3">
                            <span class="input-group-text"><i class="bi bi-search"></i></span>
                            <input id="buscarProceso" class="form-control" placeholder="Filtrar procesos..." disabled>
                        </div>
                        <div id="listaBusqueda" class="list-group procesos-riesgo-lista">
                            <div class="list-group-item text-secondary">Preparando lista...</div>
                        </div>
                    </section>
                </div>

                <div class="col-12 col-lg-6">
                    <section class="procesos-riesgo-card procesos-riesgo-card-asociados">
                        <div class="procesos-riesgo-heading">
                            <span><i class="bi bi-diagram-3"></i></span>
                            <div>
                                <strong>Procesos asociados</strong>
                                <small>Resumen activo para este riesgo.</small>
                            </div>
                            <em id="contadorProcesosAsociados">0</em>
                        </div>
                        <div id="listaProcesosAsociados" class="list-group procesos-riesgo-lista">
                            <div class="list-group-item text-secondary">Preparando lista...</div>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    `;
    modal_footer.innerHTML = `
        <button type="button" class="btn btn-secondary" onclick="cerrar_modal()">Cerrar</button>
    `;
    modal.show();
}

function actualizarEstadoProcesos(procesos) {
    const estado = document.getElementById('procesosModalEstado');
    if (!estado) return;

    if (!procesos.length) {
        estado.className = 'procesos-riesgo-status empty';
        estado.innerHTML = '<i class="bi bi-diagram-3"></i><span>Sin procesos</span>';
        return;
    }

    estado.className = 'procesos-riesgo-status ready';
    estado.innerHTML = `<i class="bi bi-check-circle"></i><span>${procesos.length} asociado${procesos.length === 1 ? '' : 's'}</span>`;
}

async function verProcesos(id) {
    mostrarCuerpoProcesos(id);
    try {
        const [respuestaAsociados, respuestaDisponibles] = await Promise.all([
            fetch(`/riesgo/${id}/procesos`),
            fetch(`/riesgo/${id}/procesos_disponibles`)
        ]);

        if (!respuestaAsociados.ok || !respuestaDisponibles.ok) {
            throw new Error('No se pudieron cargar los procesos.');
        }

        const [procesos, disponibles] = await Promise.all([
            respuestaAsociados.json(),
            respuestaDisponibles.json()
        ]);

        actualizarListaBusqueda(id, disponibles);
        actualizarListaAsociados(id, procesos);
        actualizarEstadoProcesos(procesos);
        activarBuscador();
    } catch (error) {
        const estado = document.getElementById('procesosModalEstado');
        if (estado) {
            estado.className = 'alert alert-danger mb-3';
            estado.textContent = error.message;
        } else {
            alert(error.message);
        }
    }
}

async function agregarProceso(idRiesgo, idProceso) {
    try {
        const respuesta = await fetch(
            `/riesgo/${idRiesgo}/agregar_proceso/${idProceso}`,
            {
                method: "POST"
            }
        );
        if (!respuesta.ok) {
            throw new Error("No se pudo asociar el proceso.");
        }
        await recargarProcesos(idRiesgo);
        mostrarFlash(
            "success",
            "Proceso asociado correctamente."
        );
    }
    catch (error) {
        mostrarFlash(
            "danger",
            error.message || "No se pudo asociar el proceso."
        );
    }
}

async function quitarProceso(idRiesgo,idProceso){
    try{
        const respuesta=await fetch(
            `/riesgo/${idRiesgo}/quitar_proceso/${idProceso}`,
            {
                method:"POST"
            }
        );
        if(!respuesta.ok){
            throw new Error(
                "No se pudo quitar el proceso."
            );
        }
        await recargarProcesos(idRiesgo);
        mostrarFlash(
            "info",
            "Proceso retirado correctamente."
        );
    }
    catch(error){
        mostrarFlash(
            "danger",
            error.message || "No se pudo quitar el proceso."
        );
    }
}

async function recargarProcesos(idRiesgo) {
    const [asociados, disponibles] = await Promise.all([
        fetch(`/riesgo/${idRiesgo}/procesos`),
        fetch(`/riesgo/${idRiesgo}/procesos_disponibles`)
    ]);

    if (!asociados.ok || !disponibles.ok) {
        throw new Error('No se pudieron actualizar los procesos.');
    }

    const [procesos, lista] = await Promise.all([
        asociados.json(),
        disponibles.json()
    ]);

    actualizarListaBusqueda(idRiesgo, lista);
    actualizarListaAsociados(idRiesgo, procesos);
    actualizarEstadoProcesos(procesos);
    activarBuscador();
}

function activarBuscador() {
    const buscador = document.getElementById('buscarProceso');
    if (!buscador) return;

    buscador.disabled = false;
    buscador.oninput = function() {
        const texto = this.value.trim().toLowerCase();
        document.querySelectorAll('#listaBusqueda .list-group-item[data-nombre]')
            .forEach((item) => {
                item.classList.toggle('d-none', !item.dataset.nombre.includes(texto));
            });
    };
}

function actualizarListaBusqueda(idRiesgo, disponibles) {
    const contenedor = document.getElementById('listaBusqueda');
    if (!contenedor) return;

    contenedor.innerHTML = disponibles.length
        ? disponibles.map((proceso) => construirItemProcesoDisponible(idRiesgo, proceso)).join('')
        : '<div class="list-group-item text-secondary">No hay procesos disponibles para asociar.</div>';
}

function actualizarListaAsociados(idRiesgo, procesos) {
    const contenedor = document.getElementById('listaProcesosAsociados');
    const contador = document.getElementById('contadorProcesosAsociados');
    if (!contenedor) return;

    contenedor.innerHTML = procesos.length
        ? procesos.map((proceso) => construirItemProcesoAsociado(idRiesgo, proceso)).join('')
        : '<div class="list-group-item text-secondary">Sin procesos asociados.</div>';

    if (contador) {
        contador.textContent = procesos.length;
    }
}

function mostrarFlash(tipo, texto) {
    // Unificar con mostrar_mensaje_modal (alerta flotante en esquina superior derecha)
    mostrar_mensaje_modal(texto, tipo);
}

window.obtenerColorRiesgoMapa = obtenerColorRiesgoMapa;
window.calcularNivelRiesgo = calcularNivelRiesgo;
window.obtenerColorNivelRiesgo = obtenerColorNivelRiesgo;
window.ver_control = ver_control;
window.eliminarControl = eliminarControl;
