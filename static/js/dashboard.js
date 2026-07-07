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

        default:
            break;
    }

    if (modal_dialog) {
        modal_dialog.className = modalClass;
    }
    modal_footer.innerHTML = botones;
    modal_cuerpo.innerHTML = html;
    modal_titulo.innerHTML = titulo;
    modal.show();
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
