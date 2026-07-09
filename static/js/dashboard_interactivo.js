document.addEventListener('DOMContentLoaded', function () {
                        const datos = window.dashboardRiesgosData || {};
                        const procesos = datos.procesos_detalle || [];
                        const riesgos = datos.riesgos_detalle || [];
                        const procesoSelect = document.getElementById('dashProcesoFiltro');
                        const grupoWrap = document.getElementById('dashGrupoFiltro');
                        const riskList = document.getElementById('dashRiskList');
                        const heatGrid = document.getElementById('dashHeatGrid');
                        const riesgoResumen = document.getElementById('dashRiesgoResumen');
                        const detalleTitulo = document.getElementById('dashDetalleTitulo');
                        const detalleNivel = document.getElementById('dashDetalleNivel');
                        const detalleContenido = document.getElementById('dashDetalleContenido');
                        let riesgoActivo = null;
                        let cuadranteActivo = null;

                        const colores = [
                            ['#fbbf24','#f97316','#f97316','#ef4444','#ef4444'],
                            ['#22c55e','#fbbf24','#f97316','#f97316','#ef4444'],
                            ['#22c55e','#fbbf24','#fbbf24','#f97316','#f97316'],
                            ['#22c55e','#22c55e','#fbbf24','#fbbf24','#f97316'],
                            ['#d9ead3','#22c55e','#22c55e','#22c55e','#fbbf24']
                        ];
                        const nivelClase = {
                            'MUY BAJO': 'nivel-muy-bajo',
                            BAJO: 'nivel-bajo',
                            MEDIO: 'nivel-medio',
                            ALTO: 'nivel-alto',
                            EXTREMO: 'nivel-extremo'
                        };
                        const texto = (valor) => String(valor || '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
                        const formato = (valor) => texto(String(valor || '-').replaceAll('_', ' '));
                        const numero = (valor) => Number(valor || 0).toLocaleString('es-PE', { maximumFractionDigits: 2 });
                        const porcentaje = (valor) => `${numero(valor)}%`;

                        function riesgosFiltrados() {
                            const idProceso = procesoSelect.value;
                            if (!idProceso) {
                                return [];
                            }
                            let filtrados = riesgos.filter((riesgo) => riesgo.procesos.some((p) => String(p.id_proceso) === idProceso));
                            if (cuadranteActivo) {
                                filtrados = filtrados.filter((riesgo) => riesgo.impacto_valor === cuadranteActivo.impacto && riesgo.probabilidad_valor === cuadranteActivo.probabilidad);
                            }
                            return filtrados;
                        }

                        function renderGrupos() {
                            const idProceso = procesoSelect.value;
                            if (!idProceso) {
                                grupoWrap.className = 'dash-group-filter disabled';
                                grupoWrap.innerHTML = 'Seleccione un proceso';
                                return;
                            }
                            const proceso = procesos.find((item) => String(item.id_proceso) === idProceso);
                            if (!proceso) return;
                            const grupo = proceso.grupo;
                            const integrantes = grupo.integrantes || [];
                            grupoWrap.className = 'dash-group-filter';
                            grupoWrap.innerHTML = `
                                <div class="dash-group-chip" tabindex="0">
                                    <i class="bi bi-people-fill"></i>
                                    <span>${texto(grupo.nombre)}</span>
                                    <strong>${integrantes.length}</strong>
                                    <div class="dash-members-popover">
                                        <b>${texto(grupo.nombre)}</b>
                                        ${integrantes.length ? integrantes.map((persona) => `
                                            <div class="dash-member-row">
                                                <span>${texto(persona.nombre)}</span>
                                                <small>${texto(persona.rol)} · ${texto(persona.correo)}</small>
                                            </div>
                                        `).join('') : '<small>Sin integrantes activos.</small>'}
                                    </div>
                                </div>
                            `;
                        }

                        function renderHeatmap(baseRiesgos) {
                            const conteo = Array.from({ length: 5 }, () => Array(5).fill(0));
                            baseRiesgos.forEach((riesgo) => {
                                const x = riesgo.impacto_valor - 1;
                                const y = 5 - riesgo.probabilidad_valor;
                                if (x >= 0 && y >= 0) conteo[y][x] += 1;
                            });
                            heatGrid.innerHTML = '';
                            for (let y = 0; y < 5; y++) {
                                for (let x = 0; x < 5; x++) {
                                    const probabilidad = 5 - y;
                                    const impacto = x + 1;
                                    const valor = conteo[y][x];
                                    const cell = document.createElement('button');
                                    cell.type = 'button';
                                    cell.className = 'dash-heat-cell';
                                    cell.style.background = colores[y][x];
                                    cell.style.color = (colores[y][x] === '#d9ead3' || colores[y][x] === '#fbbf24') ? '#111827' : '#fff';
                                    const etiquetaCelda = 'Probabilidad ' + probabilidad + ', impacto ' + impacto + (valor ? ', ' + valor + ' riesgo' + (valor === 1 ? '' : 's') : '');
                                    cell.setAttribute('aria-label', etiquetaCelda);
                                    cell.title = etiquetaCelda;
                                    cell.innerHTML = valor ? '<b>' + valor + '</b>' : '';
                                    cell.classList.toggle('selected', cuadranteActivo && cuadranteActivo.impacto === impacto && cuadranteActivo.probabilidad === probabilidad);
                                    cell.addEventListener('click', () => {
                                        const mismo = cuadranteActivo && cuadranteActivo.impacto === impacto && cuadranteActivo.probabilidad === probabilidad;
                                        cuadranteActivo = mismo ? null : { impacto, probabilidad };
                                        riesgoActivo = null;
                                        renderTodo();
                                    });
                                    heatGrid.appendChild(cell);
                                }
                            }
                        }

                        function renderLista(lista) {
                            riesgoResumen.textContent = `${lista.length} riesgo${lista.length === 1 ? '' : 's'}`;
                            if (!lista.length) {
                                riskList.innerHTML = '<div class="dash-empty-mini">No hay riesgos para el filtro seleccionado.</div>';
                                renderDetalle(null);
                                return;
                            }
                            if (!riesgoActivo || !lista.some((item) => item.id_riesgo === riesgoActivo.id_riesgo)) {
                                riesgoActivo = lista[0];
                            }
                            riskList.innerHTML = lista.map((riesgo) => `
                                <button type="button" class="dash-risk-item ${riesgoActivo && riesgoActivo.id_riesgo === riesgo.id_riesgo ? 'active' : ''}" data-id="${riesgo.id_riesgo}">
                                    <span class="dash-risk-code">${texto(riesgo.codigo)}</span>
                                    <strong>${texto(riesgo.nombre)}</strong>
                                    <small>${texto(riesgo.descripcion || 'Sin descripción')}</small>
                                    <em class="nivel-riesgo-badge ${nivelClase[riesgo.nivel] || ''}">${texto(riesgo.nivel)}</em>
                                </button>
                            `).join('');
                            riskList.querySelectorAll('.dash-risk-item').forEach((btn) => {
                                btn.addEventListener('click', () => {
                                    riesgoActivo = lista.find((riesgo) => String(riesgo.id_riesgo) === btn.dataset.id);
                                    renderLista(lista);
                                    renderDetalle(riesgoActivo);
                                });
                            });
                            renderDetalle(riesgoActivo);
                        }

                        function renderDetalle(riesgo) {
                            if (!riesgo) {
                                const faltaProceso = !procesoSelect.value;
                                detalleTitulo.textContent = faltaProceso ? 'Seleccione un proceso' : 'Seleccione un riesgo';
                                detalleNivel.className = 'dash-level-pill';
                                detalleNivel.textContent = '-';
                                detalleContenido.className = 'dash-empty-state';
                                detalleContenido.innerHTML = faltaProceso
                                    ? '<i class="bi bi-diagram-3"></i><strong>Seleccione un proceso</strong><span>Luego se listarán sus riesgos, responsables y controles asociados.</span>'
                                    : '<i class="bi bi-grid-3x3-gap"></i><strong>Seleccione un cuadrante o un riesgo</strong><span>El panel mostrará responsables, procesos y controles asociados.</span>';
                                return;
                            }
                            detalleTitulo.textContent = riesgo.nombre;
                            detalleNivel.className = `dash-level-pill nivel-riesgo-badge ${nivelClase[riesgo.nivel] || ''}`;
                            detalleNivel.textContent = riesgo.nivel;
                            detalleContenido.className = 'dash-detail-content';
                            const inherente = riesgo.riesgo_inherente || {};
                            const residual = riesgo.riesgo_residual || {};
                            detalleContenido.innerHTML = `
                                <div class="dash-detail-actions">
                                    <a class="btn btn-sm btn_primario" href="/dashboard/riesgo/${riesgo.id_riesgo}/exportar_excel">
                                        <i class="bi bi-file-earmark-spreadsheet me-2"></i>Exportar detalle
                                    </a>
                                </div>
                                <div class="dash-detail-description">
                                    <span>${texto(riesgo.codigo)}</span>
                                    <p>${texto(riesgo.descripcion || 'Sin descripción registrada.')}</p>
                                </div>
                                <div class="dash-risk-flow">
                                    <article class="dash-flow-card inherente">
                                        <small>Riesgo inherente</small>
                                        <strong>${numero(inherente.riesgo_inherente_exacto ?? residual.riesgo_inherente)}</strong>
                                        <div>
                                            <span>${porcentaje(inherente.probabilidad_inicial ?? residual.probabilidad_inicial)} prob.</span>
                                            <span>${porcentaje(inherente.impacto_inicial ?? residual.impacto_inicial)} imp.</span>
                                            <span>${texto(inherente.nivel || riesgo.nivel)}</span>
                                        </div>
                                    </article>
                                    <div class="dash-flow-arrow"><i class="bi bi-arrow-right"></i></div>
                                    <article class="dash-flow-card residual">
                                        <small>Riesgo residual</small>
                                        <strong>${porcentaje(residual.probabilidad_residual)} / ${porcentaje(residual.impacto_residual)}</strong>
                                        <div><span>${texto(residual.probabilidad_residual_categoria || '-')}</span><span>${texto(residual.impacto_residual_categoria || '-')}</span></div>
                                    </article>
                                </div>
                                <div class="dash-inherent-panel">
                                    <div class="dash-section-title">
                                        <h6>Evaluación inherente</h6>
                                        <span>Matriz 5x5</span>
                                    </div>
                                    <div class="dash-residual-grid compact">
                                        <span><b>${porcentaje(inherente.probabilidad_inicial ?? residual.probabilidad_inicial)}</b><small>${texto(inherente.probabilidad_categoria || 'Probabilidad')}</small></span>
                                        <span><b>${porcentaje(inherente.impacto_inicial ?? residual.impacto_inicial)}</b><small>${texto(inherente.impacto_categoria || 'Impacto')}</small></span>
                                        <span><b>${numero(inherente.riesgo_inherente_exacto ?? residual.riesgo_inherente)}</b><small>Inherente exacto</small></span>
                                        <span><b>${numero(inherente.riesgo_inherente_categorizado ?? residual.riesgo_inherente)}</b><small>Inherente categ.</small></span>
                                    </div>
                                </div>
                                <div class="dash-residual-panel">
                                    <div class="dash-section-title">
                                        <h6>Reducción por controles</h6>
                                        <span>${residual.total_controles_evaluados || 0} evaluado${(residual.total_controles_evaluados || 0) === 1 ? '' : 's'}</span>
                                    </div>
                                    <div class="dash-residual-grid compact">
                                        <span><b>${porcentaje(residual.reduccion_promedio_probabilidad)}</b><small>Reducción prob.</small></span>
                                        <span><b>${porcentaje(residual.reduccion_promedio_impacto)}</b><small>Reducción imp.</small></span>
                                        <span><b>${porcentaje(residual.probabilidad_residual)}</b><small>Prob. residual</small></span>
                                        <span><b>${porcentaje(residual.impacto_residual)}</b><small>Imp. residual</small></span>
                                    </div>
                                </div>
                                <div class="dash-detail-section">
                                    <div class="dash-section-title"><h6>Procesos relacionados</h6></div>
                                    <div class="dash-chip-row">
                                        ${riesgo.procesos.length ? riesgo.procesos.map((p) => `<span>${texto(p.nombre)}</span>`).join('') : '<span>Sin proceso asignado</span>'}
                                    </div>
                                </div>
                                <div class="dash-detail-section">
                                    <div class="dash-section-title"><h6>Grupo responsable</h6></div>
                                    <div class="dash-responsibles">
                                        ${riesgo.grupos.length ? riesgo.grupos.map((grupo) => `
                                            <article>
                                                <strong>${texto(grupo.nombre)}</strong>
                                                ${(grupo.integrantes || []).length ? grupo.integrantes.map((persona) => `
                                                    <div><i class="bi bi-person-circle"></i><span>${texto(persona.nombre)}</span><small>${texto(persona.rol)}</small></div>
                                                `).join('') : '<small>Sin integrantes activos.</small>'}
                                            </article>
                                        `).join('') : '<article><strong>Sin grupo visible</strong><small>Asocie el riesgo a un proceso para ver responsables.</small></article>'}
                                    </div>
                                </div>
                                <div class="dash-detail-section">
                                    <div class="dash-section-title"><h6>Controles</h6><span>${residual.total_controles_evaluados || 0}</span></div>
                                    <div class="dash-control-list">
                                        ${riesgo.controles.length ? riesgo.controles.map((control) => `
                                            <article>
                                                <div><strong>${texto(control.nombre)}</strong><span>${texto(control.estado)}</span></div>
                                                <p>${texto(control.descripcion || 'Sin descripción.')}</p>
                                                <div class="dash-control-tags">
                                                    <span>Máx. ${porcentaje(control.maximo_baja_probabilidad)} / ${porcentaje(control.maximo_baja_impacto)}</span>
                                                    <span>Solidez ${texto(control.solidez_control)} (${porcentaje(control.solidez_valor)})</span>
                                                    <span>Cap. ${porcentaje(control.capacidad_real_probabilidad)} / ${porcentaje(control.capacidad_real_impacto)}</span>
                                                    <span>Mit. ${porcentaje(control.mitigacion_probabilidad)} / ${porcentaje(control.mitigacion_impacto)}</span>
                                                    <span>Red. ${porcentaje(control.reduccion_real_probabilidad)} / ${porcentaje(control.reduccion_real_impacto)}</span>
                                                </div>
                                            </article>
                                        `).join('') : '<div class="dash-empty-mini">Este riesgo aún no tiene controles asociados.</div>'}
                                    </div>
                                </div>
                            `;
                        }

                        function renderTodo() {
                            const base = procesoSelect.value
                                ? riesgos.filter((riesgo) => riesgo.procesos.some((p) => String(p.id_proceso) === procesoSelect.value))
                                : [];
                            renderGrupos();
                            renderHeatmap(base);
                            renderLista(riesgosFiltrados());
                        }

                        procesoSelect.addEventListener('change', () => {
                            cuadranteActivo = null;
                            riesgoActivo = null;
                            renderTodo();
                        });
                        renderTodo();
                    });
