document.addEventListener('DOMContentLoaded', function () {
                        const datos = window.dashboardRiesgosData || {};
                        const procesos = datos.procesos_detalle || [];
                        const riesgos = datos.riesgos_detalle || [];
                        const procesoSelect = document.getElementById('dashProcesoFiltro');
                        const grupoWrap = document.getElementById('dashGrupoFiltro');
                        const riskList = document.getElementById('dashRiskList');
                        const heatMaps = document.getElementById('dashHeatMaps');
                        const heatTitulo = document.getElementById('dashHeatTitulo');
                        const heatScope = document.getElementById('dashHeatScope');
                        const filtroInherente = document.getElementById('dashFiltroInherente');
                        const filtroResidual = document.getElementById('dashFiltroResidual');
                        const riesgoResumen = document.getElementById('dashRiesgoResumen');
                        const detalleTitulo = document.getElementById('dashDetalleTitulo');
                        const detalleNivel = document.getElementById('dashDetalleNivel');
                        const detalleContenido = document.getElementById('dashDetalleContenido');
                        if (!procesoSelect || !grupoWrap || !riskList || !heatMaps || !heatTitulo || !heatScope || !filtroInherente || !filtroResidual || !riesgoResumen || !detalleTitulo || !detalleNivel || !detalleContenido) {
                            return;
                        }
                        let riesgoActivo = null;
                        let riesgoFijadoMapa = false;
                        let cuadranteActivo = null;

                        const colores = [
                            ['#fbbf24','#f97316','#f97316','#ef4444','#ef4444'],
                            ['#22c55e','#fbbf24','#f97316','#f97316','#ef4444'],
                            ['#22c55e','#fbbf24','#fbbf24','#f97316','#f97316'],
                            ['#22c55e','#22c55e','#fbbf24','#fbbf24','#f97316'],
                            ['#d9ead3','#22c55e','#22c55e','#22c55e','#fbbf24']
                        ];
                        const ordenNivel = {
                            EXTREMO: 5,
                            ALTO: 4,
                            MEDIO: 3,
                            BAJO: 2,
                            'MUY BAJO': 1
                        };
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
                        const modosMapa = () => {
                            const modos = [];
                            if (filtroInherente.checked) modos.push('inherente');
                            if (filtroResidual.checked) modos.push('residual');
                            return modos.length ? modos : ['inherente'];
                        };
                        const etiquetaModo = (tipo) => tipo === 'residual' ? 'Residual' : 'Inherente';

                        function coordRiesgo(riesgo, tipo) {
                            if (tipo === 'residual') {
                                const residual = riesgo.riesgo_residual || {};
                                return {
                                    impacto: Math.max(1, Math.min(5, Math.round(Number(residual.impacto_residual_categorizado || 20) / 20))),
                                    probabilidad: Math.max(1, Math.min(5, Math.round(Number(residual.probabilidad_residual_categorizada || 20) / 20)))
                                };
                            }
                            return {
                                impacto: Number(riesgo.impacto_valor || 0),
                                probabilidad: Number(riesgo.probabilidad_valor || 0)
                            };
                        }

                        function riesgosBaseProceso() {
                            const idProceso = procesoSelect.value;
                            return idProceso
                                ? riesgos.filter((riesgo) => riesgo.procesos.some((p) => String(p.id_proceso) === idProceso))
                                : [...riesgos];
                        }

                        function riesgoEnCuadrante(riesgo, cuadrante) {
                            if (!cuadrante) return true;
                            const coord = coordRiesgo(riesgo, cuadrante.tipo);
                            return coord.impacto === cuadrante.impacto && coord.probabilidad === cuadrante.probabilidad;
                        }

                        function riesgosFiltrados() {
                            let filtrados = riesgosBaseProceso();
                            if (cuadranteActivo) {
                                filtrados = filtrados.filter((riesgo) => riesgoEnCuadrante(riesgo, cuadranteActivo));
                            }
                            return filtrados.sort((a, b) => (ordenNivel[b.nivel] || 0) - (ordenNivel[a.nivel] || 0) || b.puntaje - a.puntaje);
                        }

                        function renderGrupos() {
                            const idProceso = procesoSelect.value;
                            if (!idProceso) {
                                grupoWrap.className = 'dash-group-filter disabled';
                                grupoWrap.innerHTML = 'Todos los responsables';
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
                            const modos = modosMapa();
                            const riesgosMapa = riesgoFijadoMapa && riesgoActivo ? [riesgoActivo] : baseRiesgos;
                            heatTitulo.textContent = modos.length === 2 ? 'Comparación de mapas' : `Riesgo ${etiquetaModo(modos[0]).toLowerCase()}`;
                            heatScope.textContent = riesgoFijadoMapa && riesgoActivo ? riesgoActivo.codigo : `${riesgosMapa.length} riesgo${riesgosMapa.length === 1 ? '' : 's'}`;
                            heatMaps.className = `dash-heat-maps ${modos.length === 2 ? 'dual' : 'single'}`;
                            heatMaps.innerHTML = modos.map((tipo) => construirHeatmap(riesgosMapa, tipo)).join('');
                            heatMaps.querySelectorAll('.dash-heat-cell').forEach((cell) => {
                                cell.addEventListener('click', () => {
                                    const impacto = Number(cell.dataset.impacto);
                                    const probabilidad = Number(cell.dataset.probabilidad);
                                    const tipo = cell.dataset.tipo;
                                    const mismo = cuadranteActivo && cuadranteActivo.tipo === tipo && cuadranteActivo.impacto === impacto && cuadranteActivo.probabilidad === probabilidad;
                                    cuadranteActivo = mismo ? null : { tipo, impacto, probabilidad };
                                    riesgoActivo = null;
                                    riesgoFijadoMapa = false;
                                    renderTodo();
                                });
                            });
                        }

                        function construirHeatmap(baseRiesgos, tipo) {
                            const conteo = Array.from({ length: 5 }, () => Array(5).fill(0));
                            baseRiesgos.forEach((riesgo) => {
                                const coord = coordRiesgo(riesgo, tipo);
                                const x = coord.impacto - 1;
                                const y = 5 - coord.probabilidad;
                                if (x >= 0 && x < 5 && y >= 0 && y < 5) conteo[y][x] += 1;
                            });
                            let celdas = '';
                            for (let y = 0; y < 5; y++) {
                                for (let x = 0; x < 5; x++) {
                                    const probabilidad = 5 - y;
                                    const impacto = x + 1;
                                    const valor = conteo[y][x];
                                    const etiquetaCelda = 'Probabilidad ' + probabilidad + ', impacto ' + impacto + (valor ? ', ' + valor + ' riesgo' + (valor === 1 ? '' : 's') : '');
                                    const selected = cuadranteActivo && cuadranteActivo.tipo === tipo && cuadranteActivo.impacto === impacto && cuadranteActivo.probabilidad === probabilidad;
                                    celdas += `
                                        <button type="button"
                                            class="dash-heat-cell ${selected ? 'selected' : ''}"
                                            style="background:${colores[y][x]};color:${(colores[y][x] === '#d9ead3' || colores[y][x] === '#fbbf24') ? '#111827' : '#fff'}"
                                            data-tipo="${tipo}"
                                            data-impacto="${impacto}"
                                            data-probabilidad="${probabilidad}"
                                            aria-label="${texto(etiquetaCelda)}"
                                            title="${texto(etiquetaCelda)}">
                                            ${valor ? '<b>' + valor + '</b>' : ''}
                                        </button>
                                    `;
                                }
                            }
                            return `
                                <article class="dash-heat-map-card">
                                    <div class="dash-heat-map-title">
                                        <strong>${etiquetaModo(tipo)}</strong>
                                        <span>${baseRiesgos.length} riesgo${baseRiesgos.length === 1 ? '' : 's'}</span>
                                    </div>
                                    <div class="dash-heat-layout">
                                        <div class="dash-heat-axis-y">Probabilidad</div>
                                        <div>
                                            <div class="dash-heat-axis-x">Impacto</div>
                                            <div class="dash-heat-xlabels">
                                                <span>Ins.</span><span>Men.</span><span>Mod.</span><span>May.</span><span>Cat.</span>
                                            </div>
                                            <div class="dash-heat-body">
                                                <div class="dash-heat-ylabels">
                                                    <span>C.S.</span><span>Prob.</span><span>Pos.</span><span>Imp.</span><span>Rar.</span>
                                                </div>
                                                <div class="dash-heat-grid">${celdas}</div>
                                            </div>
                                        </div>
                                    </div>
                                </article>
                            `;
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
                                <button type="button" class="dash-risk-item ${riesgoActivo && riesgoActivo.id_riesgo === riesgo.id_riesgo ? 'active' : ''} ${riesgoFijadoMapa && riesgoActivo && riesgoActivo.id_riesgo === riesgo.id_riesgo ? 'map-focus' : ''}" data-id="${riesgo.id_riesgo}">
                                    <span class="dash-risk-code">${texto(riesgo.codigo)}</span>
                                    <strong>${texto(riesgo.nombre)}</strong>
                                    <small>${texto(riesgo.descripcion || 'Sin descripción')}</small>
                                    <em class="nivel-riesgo-badge ${nivelClase[riesgo.nivel] || ''}">${texto(riesgo.nivel)}</em>
                                    ${riesgoFijadoMapa && riesgoActivo && riesgoActivo.id_riesgo === riesgo.id_riesgo ? '<i class="bi bi-crosshair dash-map-focus-icon"></i>' : ''}
                                </button>
                            `).join('');
                            riskList.querySelectorAll('.dash-risk-item').forEach((btn) => {
                                btn.addEventListener('click', () => {
                                    const seleccionado = lista.find((riesgo) => String(riesgo.id_riesgo) === btn.dataset.id);
                                    const mismo = riesgoFijadoMapa && riesgoActivo && seleccionado && riesgoActivo.id_riesgo === seleccionado.id_riesgo;
                                    riesgoActivo = seleccionado;
                                    riesgoFijadoMapa = !mismo;
                                    cuadranteActivo = null;
                                    renderTodo();
                                });
                            });
                            renderDetalle(riesgoActivo);
                        }

                        function renderDetalle(riesgo) {
                            if (!riesgo) {
                                const faltaProceso = !procesoSelect.value;
                                detalleTitulo.textContent = 'Seleccione un riesgo';
                                detalleNivel.className = 'dash-level-pill';
                                detalleNivel.textContent = '-';
                                detalleContenido.className = 'dash-empty-state';
                                detalleContenido.innerHTML = '<i class="bi bi-grid-3x3-gap"></i><strong>Seleccione un cuadrante o un riesgo</strong><span>El panel mostrará solo la información clave para decidir.</span>';
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
                                <div class="dash-residual-panel">
                                    <div class="dash-section-title">
                                        <h6>Indicadores clave</h6>
                                        <span>${residual.total_controles_evaluados || 0} evaluado${(residual.total_controles_evaluados || 0) === 1 ? '' : 's'}</span>
                                    </div>
                                    <div class="dash-residual-grid compact">
                                        <span><b>${numero(inherente.riesgo_inherente_exacto ?? residual.riesgo_inherente)}</b><small>Inherente</small></span>
                                        <span><b>${numero(residual.riesgo_residual_exacto)}</b><small>Residual</small></span>
                                        <span><b>${porcentaje(residual.reduccion_promedio_probabilidad)}</b><small>Reducción prob.</small></span>
                                        <span><b>${porcentaje(residual.reduccion_promedio_impacto)}</b><small>Reducción imp.</small></span>
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
                            const base = riesgosBaseProceso();
                            renderGrupos();
                            renderHeatmap(base);
                            renderLista(riesgosFiltrados());
                        }

                        function riesgosBaseExportacion() {
                            if (riesgoFijadoMapa && riesgoActivo) {
                                return [riesgoActivo];
                            }
                            const idProceso = procesoSelect.value;
                            return idProceso
                                ? riesgos.filter((riesgo) => riesgo.procesos.some((p) => String(p.id_proceso) === idProceso))
                                : riesgos;
                        }

                        function contarMapa(lista, tipo) {
                            const conteo = Array.from({ length: 5 }, () => Array(5).fill(0));
                            lista.forEach((riesgo) => {
                                const coord = coordRiesgo(riesgo, tipo);
                                const x = coord.impacto - 1;
                                const y = 5 - coord.probabilidad;
                                if (x >= 0 && x < 5 && y >= 0 && y < 5) conteo[y][x] += 1;
                            });
                            return conteo;
                        }

                        function dibujarMapa(ctx, conteo, x0, y0, titulo) {
                            const celda = 58;
                            const gap = 5;
                            const labelsX = ['Ins.', 'Men.', 'Mod.', 'May.', 'Cat.'];
                            const labelsY = ['C.S.', 'Prob.', 'Pos.', 'Imp.', 'Rar.'];
                            ctx.fillStyle = '#111827';
                            ctx.font = '700 20px Inter, Arial';
                            ctx.fillText(titulo, x0, y0);
                            ctx.font = '700 12px Inter, Arial';
                            ctx.fillStyle = '#64748b';
                            labelsX.forEach((label, i) => ctx.fillText(label, x0 + 46 + i * (celda + gap) + 15, y0 + 32));
                            labelsY.forEach((label, i) => ctx.fillText(label, x0, y0 + 58 + i * (celda + gap) + 34));
                            for (let y = 0; y < 5; y++) {
                                for (let x = 0; x < 5; x++) {
                                    const cx = x0 + 46 + x * (celda + gap);
                                    const cy = y0 + 44 + y * (celda + gap);
                                    ctx.fillStyle = colores[y][x];
                                    ctx.beginPath();
                                    ctx.roundRect(cx, cy, celda, celda, 10);
                                    ctx.fill();
                                    const valor = conteo[y][x];
                                    if (valor) {
                                        ctx.fillStyle = '#111827';
                                        ctx.font = '800 20px Inter, Arial';
                                        ctx.textAlign = 'center';
                                        ctx.fillText(String(valor), cx + celda / 2, cy + 36);
                                        ctx.textAlign = 'left';
                                    }
                                }
                            }
                        }

                        function exportarImagenComparativa() {
                            const lista = riesgosBaseExportacion();
                            const canvas = document.createElement('canvas');
                            canvas.width = 920;
                            canvas.height = 500;
                            const ctx = canvas.getContext('2d');
                            ctx.fillStyle = '#f8fafc';
                            ctx.fillRect(0, 0, canvas.width, canvas.height);
                            ctx.fillStyle = '#111827';
                            ctx.font = '800 26px Inter, Arial';
                            ctx.fillText('Comparación de mapas de riesgo', 36, 44);
                            ctx.fillStyle = '#64748b';
                            ctx.font = '500 14px Inter, Arial';
                            const proceso = procesoSelect.value
                                ? procesos.find((item) => String(item.id_proceso) === procesoSelect.value)?.nombre
                                : 'Todos los procesos';
                            ctx.fillText(`${proceso || 'Todos los procesos'} · ${lista.length} riesgo${lista.length === 1 ? '' : 's'}`, 36, 68);
                            dibujarMapa(ctx, contarMapa(lista, 'inherente'), 36, 110, 'Riesgo inherente');
                            dibujarMapa(ctx, contarMapa(lista, 'residual'), 494, 110, 'Riesgo residual');
                            ctx.fillStyle = '#64748b';
                            ctx.font = '600 12px Inter, Arial';
                            ctx.fillText('Escala: probabilidad vertical e impacto horizontal. El número indica cantidad de riesgos por celda.', 36, 474);
                            const link = document.createElement('a');
                            link.download = 'comparacion_mapa_riesgos.png';
                            link.href = canvas.toDataURL('image/png');
                            link.click();
                        }

                        procesoSelect.addEventListener('change', () => {
                            cuadranteActivo = null;
                            riesgoActivo = null;
                            riesgoFijadoMapa = false;
                            renderTodo();
                        });
                        [filtroInherente, filtroResidual].forEach((input) => {
                            input.addEventListener('change', () => {
                                if (!filtroInherente.checked && !filtroResidual.checked) {
                                    input.checked = true;
                                }
                                document.querySelectorAll('.dash-risk-toggle').forEach((label) => {
                                    const control = label.querySelector('input');
                                    label.classList.toggle('active', Boolean(control?.checked));
                                });
                                cuadranteActivo = null;
                                renderTodo();
                            });
                        });
                        document.getElementById('dashExportImagen')?.addEventListener('click', exportarImagenComparativa);
                        renderTodo();
                    });
