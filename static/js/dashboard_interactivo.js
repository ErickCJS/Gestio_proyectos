document.addEventListener('DOMContentLoaded', function () {
                        const datos = window.dashboardRiesgosData || {};
                        const procesos = datos.procesos_detalle || [];
                        const riesgos = datos.riesgos_detalle || [];
                        const procesoSelect = document.getElementById('dashProcesoFiltro');
                        const grupoWrap = document.getElementById('dashGrupoFiltro');
                        const riskList = document.getElementById('dashRiskList');
                        const heatGrid = document.getElementById('dashHeatGrid');
                        const heatTotal = document.getElementById('dashHeatTotal');
                        const riesgoResumen = document.getElementById('dashRiesgoResumen');
                        const detalleTitulo = document.getElementById('dashDetalleTitulo');
                        const detalleNivel = document.getElementById('dashDetalleNivel');
                        const detalleContenido = document.getElementById('dashDetalleContenido');
                        const residual = document.getElementById('dashFiltroResidual');
                        const inherente = document.getElementById('dashFiltroInherente');
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

                        function riesgosFiltrados() {
                            const idProceso = procesoSelect.value;
                            let filtrados = riesgos;
                            if (idProceso) {
                                filtrados = riesgos.filter((riesgo) => riesgo.procesos.some((p) => String(p.id_proceso) === idProceso));
                            }
                            if (cuadranteActivo) {
                                filtrados = filtrados.filter((riesgo) => riesgo.impacto_valor === cuadranteActivo.impacto && riesgo.probabilidad_valor === cuadranteActivo.probabilidad);
                            }
                            return filtrados;
                        }

                        function actualizarToggles() {
                            document.querySelectorAll('.dash-risk-toggle').forEach((label) => {
                                label.classList.toggle('active', label.querySelector('input').checked);
                            });
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
                                    cell.innerHTML = `<span>${probabilidad * impacto}</span>${valor ? `<b>${valor}</b>` : ''}`;
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
                            heatTotal.textContent = baseRiesgos.length;
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
                                detalleTitulo.textContent = 'Seleccione un riesgo';
                                detalleNivel.className = 'dash-level-pill';
                                detalleNivel.textContent = '-';
                                detalleContenido.className = 'dash-empty-state';
                                detalleContenido.innerHTML = '<i class="bi bi-grid-3x3-gap"></i><strong>Seleccione un cuadrante o un riesgo</strong><span>El panel mostrará responsables, procesos y controles asociados.</span>';
                                return;
                            }
                            detalleTitulo.textContent = riesgo.nombre;
                            detalleNivel.className = `dash-level-pill nivel-riesgo-badge ${nivelClase[riesgo.nivel] || ''}`;
                            detalleNivel.textContent = riesgo.nivel;
                            detalleContenido.className = 'dash-detail-content';
                            detalleContenido.innerHTML = `
                                <div class="dash-detail-actions">
                                    <a class="btn btn-sm btn_primario" href="/dashboard/riesgo/${riesgo.id_riesgo}/exportar_excel">
                                        <i class="bi bi-file-earmark-spreadsheet me-2"></i>Exportar detalle
                                    </a>
                                </div>
                                <p>${texto(riesgo.descripcion || 'Sin descripción registrada.')}</p>
                                <div class="dash-detail-metrics">
                                    <span><b>${riesgo.puntaje}</b><small>Puntaje</small></span>
                                    <span><b>${formato(riesgo.impacto)}</b><small>Impacto</small></span>
                                    <span><b>${formato(riesgo.probabilidad)}</b><small>Probabilidad</small></span>
                                </div>
                                <div class="dash-detail-section">
                                    <h6>Procesos relacionados</h6>
                                    <div class="dash-chip-row">
                                        ${riesgo.procesos.length ? riesgo.procesos.map((p) => `<span>${texto(p.nombre)}</span>`).join('') : '<span>Sin proceso asignado</span>'}
                                    </div>
                                </div>
                                <div class="dash-detail-section">
                                    <h6>Grupo responsable</h6>
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
                                    <h6>Controles asociados</h6>
                                    <div class="dash-control-list">
                                        ${riesgo.controles.length ? riesgo.controles.map((control) => `
                                            <article>
                                                <div><strong>${texto(control.nombre)}</strong><span>${texto(control.tipo)}</span></div>
                                                <p>${texto(control.descripcion || 'Sin descripción.')}</p>
                                                <small>Impacto: ${texto(control.impacto)} · Probabilidad: ${texto(control.probabilidad)} · ${texto(control.estado)}</small>
                                            </article>
                                        `).join('') : '<div class="dash-empty-mini">Este riesgo aún no tiene controles asociados.</div>'}
                                    </div>
                                </div>
                            `;
                        }

                        function renderTodo() {
                            const base = procesoSelect.value
                                ? riesgos.filter((riesgo) => riesgo.procesos.some((p) => String(p.id_proceso) === procesoSelect.value))
                                : riesgos;
                            renderGrupos();
                            renderHeatmap(base);
                            renderLista(riesgosFiltrados());
                        }

                        procesoSelect.addEventListener('change', () => {
                            cuadranteActivo = null;
                            riesgoActivo = null;
                            renderTodo();
                        });
                        [residual, inherente].forEach((input) => input.addEventListener('change', actualizarToggles));
                        actualizarToggles();
                        renderTodo();
                    });
