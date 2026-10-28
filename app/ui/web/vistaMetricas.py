# ruff: noqa: N999
"""Vista de Métricas y Analítica, Auditoría de Cuellos de Botella y Filtros Avanzados.

Implementa los requerimientos RF-07 y RF-08 (EARS-07.1 a EARS-07.5):
- Resumen cuantitativo: total de tareas activas, desglose por columnas y conteo de descartadas.
- Barras de progreso de avance porcentual global y por paquete EDT individual.
- Manejo seguro de proyectos sin tareas activas mostrando 0.0% y leyenda 'Sin tareas registradas' sin división por cero.
- Distribución de carga observable por integrante (asignadas y completadas) sin scoring ni clasificaciones no aprobadas.
- Sección de auditoría de cuellos de botella (contadorRegresos > 0) ordenada descendentemente con motivos históricos.
- Sub-panel de filtros interactivos combinables (estado, responsable, prioridad, solo vencidas, solo inactivas).
- Ordenamiento reactivo por fecha objetivo o prioridad consumiendo funciones puras de app/core/filtros.py.
- Enlace de retorno directo al Workspace del proyecto activo.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from reactpy import component, html, use_state
from reactpy.types import VdomDict

from app.core.edt import calcularAvancePaquete, obtenerTareasActivas
from app.core.filtros import (
    crearCriterioFiltro,
    filtrarTareas,
    ordenarPorFecha,
    ordenarPorPrioridad,
)
from app.core.metricas import (
    auditarCuellosDeBotella,
    calcularAvanceGlobal,
    calcularCargaIntegrantes,
    calcularResumenTareas,
)
from app.domain.catalogos import EstadoKanban, PrioridadTarea
from app.domain.modelos import Proyecto, Tarea
from app.domain.monadas import Alguno, Ninguno, Opcion
from app.ui.web.estilos import (
    BOTON_PRIMARIO,
    INPUT_TEXTO,
    obtenerClaseEstadoKanban,
    obtenerClasePrioridad,
)


@component
def vistaMetricas(
    proyecto: Proyecto,
    alVolverWorkspace: Callable[[], None],
) -> VdomDict:
    """Componente de panel de métricas ejecutivas, cuellos de botella y filtros analíticos."""
    # -------------------------------------------------------------------------
    # 1. Estados Locales de Filtros y Ordenamiento
    # -------------------------------------------------------------------------
    filtroEstado, setFiltroEstado = use_state("")
    filtroResponsable, setFiltroResponsable = use_state("")
    filtroPrioridad, setFiltroPrioridad = use_state("")
    soloVencidas, setSoloVencidas = use_state(False)
    criterioOrden, setCriterioOrden = use_state("FECHA")  # "FECHA" o "PRIORIDAD"

    # Tarea expandida en cuellos de botella para ver motivos
    tareaExpandidaMotivos, setTareaExpandidaMotivos = use_state("")

    # -------------------------------------------------------------------------
    # 2. Recopilación y Cálculos Puros del Proyecto
    # -------------------------------------------------------------------------
    todasLasTareas: tuple[Tarea, ...] = tuple(
        t for paq in proyecto.paquetes for t in paq.tareas
    )
    resumen = calcularResumenTareas(todasLasTareas)
    avanceGlobal = calcularAvanceGlobal(todasLasTareas)
    cargasPorMiembro = calcularCargaIntegrantes(proyecto.integrantes, todasLasTareas)
    cuellosDeBotella = auditarCuellosDeBotella(todasLasTareas)

    totalActivas = resumen["totalActivas"]
    totalInactivas = resumen["totalInactivas"]

    # Conteo de tareas sin asignar
    tareasSinAsignar = sum(
        1 for t in todasLasTareas if t.activo and t.cedulaResponsable.esNinguno()
    )

    # -------------------------------------------------------------------------
    # 3. Aplicación de Filtros y Ordenamiento Analítico (HOF y Closures)
    # -------------------------------------------------------------------------
    esFiltroDescartadas = filtroEstado == "DESCARTADAS"
    opcionEstado: Opcion[EstadoKanban] = (
        Alguno(EstadoKanban(filtroEstado))
        if (filtroEstado and not esFiltroDescartadas)
        else Ninguno()
    )
    opcionResponsable: Opcion[str] = (
        Alguno(filtroResponsable) if filtroResponsable else Ninguno()
    )
    opcionPrioridad: Opcion[PrioridadTarea] = (
        Alguno(PrioridadTarea(filtroPrioridad)) if filtroPrioridad else Ninguno()
    )

    fechaHoy = datetime.now().strftime("%Y-%m-%d")
    criterioPredicado = crearCriterioFiltro(
        estado=opcionEstado,
        cedula=opcionResponsable,
        prioridad=opcionPrioridad,
        soloVencidas=soloVencidas,
        soloInactivas=esFiltroDescartadas,
        fechaReferencia=fechaHoy,
    )

    tareasFiltradas = filtrarTareas(todasLasTareas, criterioPredicado)
    if criterioOrden == "PRIORIDAD":
        tareasOrdenadas = ordenarPorPrioridad(tareasFiltradas)
    else:
        tareasOrdenadas = ordenarPorFecha(tareasFiltradas)

    # -------------------------------------------------------------------------
    # 4. Construcción de Secciones Visuales
    # -------------------------------------------------------------------------

    # A. KPI Cards
    kpis = html.div(
        {
            "id": "kpis-metricas-grid",
            "className": "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4",
        },
        # Total Activas
        html.div(
            {
                "id": "card-total-activas",
                "className": "p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-2",
            },
            html.div(
                {"className": "flex items-center justify-between"},
                html.span(
                    {
                        "className": "text-xs font-bold text-slate-500 uppercase tracking-wider"
                    },
                    "Tareas Activas",
                ),
                html.span({"className": "text-lg"}, "📋"),
            ),
            html.div(
                {"className": "flex items-baseline space-x-2"},
                html.span(
                    {
                        "id": "metrica-total-activas",
                        "className": "text-3xl font-extrabold text-slate-900",
                    },
                    str(totalActivas),
                ),
                html.span({"className": "text-xs text-slate-400"}, "en tablero"),
            ),
            html.p(
                {"className": "text-xs text-slate-500 pt-1"},
                f"{totalActivas} tareas distribuidas en {len(proyecto.paquetes)} paquetes",
            ),
        ),
        # Desglose Kanban
        html.div(
            {
                "id": "card-desglose-kanban",
                "className": "p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-2",
            },
            html.div(
                {"className": "flex items-center justify-between"},
                html.span(
                    {
                        "className": "text-xs font-bold text-slate-500 uppercase tracking-wider"
                    },
                    "Distribución Kanban",
                ),
                html.span({"className": "text-lg"}, "📊"),
            ),
            html.div(
                {"className": "grid grid-cols-2 gap-2 pt-1 text-xs"},
                html.div(
                    {"className": "flex items-center space-x-1.5"},
                    html.span({"className": "w-2 h-2 rounded-full bg-slate-400"}),
                    html.span({"className": "text-slate-600"}, "Pend:"),
                    html.span(
                        {
                            "id": "metrica-conteo-pendiente",
                            "className": "font-bold text-slate-900",
                        },
                        str(resumen[EstadoKanban.PENDIENTE.value]),
                    ),
                ),
                html.div(
                    {"className": "flex items-center space-x-1.5"},
                    html.span({"className": "w-2 h-2 rounded-full bg-blue-500"}),
                    html.span({"className": "text-slate-600"}, "Prog:"),
                    html.span(
                        {
                            "id": "metrica-conteo-en-progreso",
                            "className": "font-bold text-slate-900",
                        },
                        str(resumen[EstadoKanban.EN_PROGRESO.value]),
                    ),
                ),
                html.div(
                    {"className": "flex items-center space-x-1.5"},
                    html.span({"className": "w-2 h-2 rounded-full bg-amber-500"}),
                    html.span({"className": "text-slate-600"}, "Rev:"),
                    html.span(
                        {
                            "id": "metrica-conteo-en-revision",
                            "className": "font-bold text-slate-900",
                        },
                        str(resumen[EstadoKanban.EN_REVISION.value]),
                    ),
                ),
                html.div(
                    {"className": "flex items-center space-x-1.5"},
                    html.span({"className": "w-2 h-2 rounded-full bg-emerald-500"}),
                    html.span({"className": "text-slate-600"}, "Term:"),
                    html.span(
                        {
                            "id": "metrica-conteo-terminada",
                            "className": "font-bold text-emerald-700",
                        },
                        str(resumen[EstadoKanban.TERMINADA.value]),
                    ),
                ),
            ),
        ),
        # Tareas Descartadas
        html.div(
            {
                "id": "card-total-inactivas",
                "className": "p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-2",
            },
            html.div(
                {"className": "flex items-center justify-between"},
                html.span(
                    {
                        "className": "text-xs font-bold text-slate-500 uppercase tracking-wider"
                    },
                    "Descartadas (Auditoría)",
                ),
                html.span({"className": "text-lg"}, "🗑️"),
            ),
            html.div(
                {"className": "flex items-baseline space-x-2"},
                html.span(
                    {
                        "id": "metrica-total-inactivas",
                        "className": "text-3xl font-extrabold text-slate-600",
                    },
                    str(totalInactivas),
                ),
                html.span({"className": "text-xs text-slate-400"}, "activo = 0"),
            ),
            html.p(
                {"className": "text-xs text-slate-400 pt-1"},
                "Preservadas para trazabilidad forense",
            ),
        ),
        # Avance Global
        html.div(
            {
                "id": "card-avance-global",
                "className": "p-5 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-2",
            },
            html.div(
                {"className": "flex items-center justify-between"},
                html.span(
                    {
                        "className": "text-xs font-bold text-slate-500 uppercase tracking-wider"
                    },
                    "Avance Global EDT",
                ),
                html.span({"className": "text-lg"}, "🎯"),
            ),
            html.div(
                {"className": "flex items-baseline space-x-2"},
                html.span(
                    {
                        "id": "porcentaje-avance-global",
                        "className": "text-3xl font-extrabold text-indigo-600",
                    },
                    f"{avanceGlobal}%",
                ),
                (
                    html.span(
                        {
                            "id": "texto-sin-tareas-global",
                            "className": "text-xs text-slate-400 font-medium",
                        },
                        "Sin tareas registradas",
                    )
                    if totalActivas == 0
                    else html.span(
                        {"className": "text-xs text-slate-500"},
                        f"{resumen[EstadoKanban.TERMINADA.value]} de {totalActivas} terminadas",
                    )
                ),
            ),
            # Barra progreso global
            html.div(
                {
                    "className": "w-full h-2 rounded-full bg-slate-100 overflow-hidden mt-2",
                },
                html.div(
                    {
                        "id": "barra-progreso-global",
                        "className": "h-full bg-indigo-600 transition-all duration-300 rounded-full",
                        "style": f"width: {avanceGlobal}%;",
                    }
                ),
            ),
        ),
    )

    # B. Paquetes EDT y Avance Individual (EARS-07.2 y EARS-07.5)
    filasPaquetes = []
    for paq in proyecto.paquetes:
        tareasActivasPaq = obtenerTareasActivas(paq)
        avancePaq = calcularAvancePaquete(paq)
        tieneTareasPaq = len(tareasActivasPaq) > 0
        terminadasPaq = sum(
            1 for t in tareasActivasPaq if t.estado == EstadoKanban.TERMINADA
        )

        filasPaquetes.append(
            html.div(
                {
                    "id": f"paquete-metrica-{paq.idPaquete}",
                    "className": "p-4 rounded-xl bg-slate-50/80 border border-slate-200/60 space-y-2 hover:bg-slate-100/60 transition-colors",
                },
                html.div(
                    {"className": "flex items-center justify-between text-xs"},
                    html.div(
                        {"className": "flex items-center space-x-2 min-w-0"},
                        html.span(
                            {"className": "font-mono font-bold text-slate-400"},
                            paq.idPaquete,
                        ),
                        html.span(
                            {
                                "className": "font-semibold text-slate-800 truncate max-w-[200px]"
                            },
                            paq.nombre,
                        ),
                    ),
                    html.div(
                        {"className": "flex items-center space-x-2"},
                        (
                            html.span(
                                {
                                    "id": f"paquete-sin-tareas-{paq.idPaquete}",
                                    "className": "text-[11px] text-slate-400 italic",
                                },
                                "Sin tareas registradas",
                            )
                            if not tieneTareasPaq
                            else html.span(
                                {"className": "text-[11px] text-slate-500 font-medium"},
                                f"{terminadasPaq}/{len(tareasActivasPaq)} terminadas",
                            )
                        ),
                        html.span(
                            {
                                "id": f"porcentaje-paquete-{paq.idPaquete}",
                                "className": "font-bold font-mono text-slate-900 text-xs px-2 py-0.5 rounded bg-white border border-slate-200",
                            },
                            f"{avancePaq}%",
                        ),
                    ),
                ),
                html.div(
                    {
                        "className": "w-full h-2 rounded-full bg-slate-200/70 overflow-hidden",
                    },
                    html.div(
                        {
                            "id": f"barra-paquete-{paq.idPaquete}",
                            "className": "h-full bg-indigo-500 transition-all duration-300 rounded-full",
                            "style": f"width: {avancePaq}%;",
                        }
                    ),
                ),
            )
        )

    seccionPaquetes = html.div(
        {
            "id": "seccion-avance-paquetes",
            "className": "p-6 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-4",
        },
        html.div(
            {"className": "flex items-center justify-between"},
            html.div(
                {"className": "space-y-0.5"},
                html.h3(
                    {
                        "className": "text-sm font-bold text-slate-900 uppercase tracking-wider"
                    },
                    "Avance por Paquete EDT",
                ),
                html.p(
                    {"className": "text-xs text-slate-500"},
                    "Porcentaje de completitud basado exclusivamente en tareas activas finalizadas.",
                ),
            ),
            html.span(
                {
                    "className": "text-xs font-mono font-bold text-slate-400 bg-slate-100 px-2 py-0.5 rounded"
                },
                f"{len(proyecto.paquetes)} paquetes",
            ),
        ),
        html.div(
            {"className": "space-y-3"},
            *filasPaquetes,
        ),
    )

    # C. Distribución de Carga por Integrante (EARS-07.2: solo observables, PROHIBIDO scoring)
    filasIntegrantes = []
    for miembro in proyecto.integrantes:
        datosCarga = cargasPorMiembro.get(
            miembro.cedula, {"asignadas": 0, "terminadas": 0}
        )
        asig = datosCarga["asignadas"]
        term = datosCarga["terminadas"]
        pct = round((term / asig) * 100.0, 1) if asig > 0 else 0.0
        iniciales = "".join(p[0].upper() for p in miembro.nombre.split() if p)[:2]

        filasIntegrantes.append(
            html.div(
                {
                    "id": f"miembro-carga-{miembro.cedula}",
                    "className": "p-3.5 rounded-xl bg-slate-50/80 border border-slate-200/60 flex items-center justify-between gap-4",
                },
                html.div(
                    {"className": "flex items-center space-x-3 min-w-0"},
                    html.div(
                        {
                            "className": "w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 font-bold text-xs flex items-center justify-center flex-shrink-0",
                        },
                        iniciales,
                    ),
                    html.div(
                        {"className": "space-y-0.5 min-w-0"},
                        html.p(
                            {
                                "className": "text-xs font-semibold text-slate-800 truncate"
                            },
                            miembro.nombre,
                        ),
                        html.p(
                            {"className": "text-[11px] text-slate-400 truncate"},
                            miembro.cargo.value,
                        ),
                    ),
                ),
                html.div(
                    {"className": "flex items-center space-x-4 flex-shrink-0 text-xs"},
                    html.div(
                        {"className": "text-right space-y-0.5"},
                        html.span(
                            {
                                "id": f"conteo-asignadas-{miembro.cedula}",
                                "className": "font-bold text-slate-800",
                            },
                            f"{asig} asignadas",
                        ),
                        html.span(
                            {
                                "id": f"conteo-terminadas-{miembro.cedula}",
                                "className": "text-slate-400 block text-[11px]",
                            },
                            f"{term} completadas ({pct}%)",
                        ),
                    ),
                ),
            )
        )

    seccionEquipo = html.div(
        {
            "id": "seccion-carga-equipo",
            "className": "p-6 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-4",
        },
        html.div(
            {"className": "flex items-center justify-between"},
            html.div(
                {"className": "space-y-0.5"},
                html.h3(
                    {
                        "className": "text-sm font-bold text-slate-900 uppercase tracking-wider"
                    },
                    "Distribución del Equipo Técnico",
                ),
                html.p(
                    {"className": "text-xs text-slate-500"},
                    "Conteos observables de tareas activas asignadas y terminadas por integrante.",
                ),
            ),
            (
                html.span(
                    {
                        "id": "conteo-tareas-sin-asignar",
                        "className": "text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded",
                    },
                    f"{tareasSinAsignar} sin asignar",
                )
                if tareasSinAsignar > 0
                else html.span()
            ),
        ),
        html.div(
            {"className": "space-y-2.5"},
            (
                filasIntegrantes
                if filasIntegrantes
                else html.p(
                    {"className": "text-xs text-slate-400 italic p-4 text-center"},
                    "No hay integrantes registrados en este proyecto.",
                )
            ),
        ),
    )

    # D. Auditoría de Cuellos de Botella (EARS-07.3)
    filasCuellos = []
    if len(cuellosDeBotella) > 0:
        for t in cuellosDeBotella:
            estaAbierto = tareaExpandidaMotivos == t.idTarea
            transicionesConMotivo = [
                tr for tr in t.historial if tr.comentario.esAlguno()
            ]

            def alternarExpandir(idT: str = t.idTarea) -> None:
                setTareaExpandidaMotivos("" if tareaExpandidaMotivos == idT else idT)

            filasCuellos.append(
                html.div(
                    {
                        "id": f"cuello-botella-tarea-{t.idTarea}",
                        "className": "p-4 rounded-xl bg-amber-50/60 border border-amber-200/80 space-y-2.5",
                    },
                    html.div(
                        {"className": "flex items-start justify-between gap-3"},
                        html.div(
                            {"className": "space-y-1 min-w-0"},
                            html.div(
                                {"className": "flex items-center space-x-2"},
                                html.span(
                                    {
                                        "className": "font-mono font-bold text-xs text-amber-900"
                                    },
                                    t.idTarea,
                                ),
                                html.span(
                                    {
                                        "id": f"badge-regresos-{t.idTarea}",
                                        "className": (
                                            "px-2 py-0.5 rounded-full text-[11px] font-bold "
                                            "bg-amber-200/80 text-amber-900 border border-amber-300"
                                        ),
                                    },
                                    f"↩ {t.contadorRegresos} regresos",
                                ),
                                html.span(
                                    {
                                        "className": obtenerClaseEstadoKanban(t.estado),
                                    },
                                    t.estado.value,
                                ),
                            ),
                            html.h4(
                                {
                                    "className": "text-xs font-semibold text-slate-900 truncate"
                                },
                                t.titulo,
                            ),
                        ),
                        html.button(
                            {
                                "id": f"btn-expandir-motivos-{t.idTarea}",
                                "type": "button",
                                "onClick": lambda e, idT=t.idTarea: alternarExpandir(
                                    idT
                                ),
                                "className": "text-xs font-semibold text-indigo-700 hover:text-indigo-900 flex items-center space-x-1 flex-shrink-0 pt-0.5",
                            },
                            html.span("Detalles" if estaAbierto else "Ver motivos"),
                            html.span("▲" if estaAbierto else "▼"),
                        ),
                    ),
                    (
                        html.div(
                            {
                                "id": f"motivos-regreso-{t.idTarea}",
                                "className": "pt-2 mt-2 border-t border-amber-200/60 space-y-2 text-xs",
                            },
                            html.span(
                                {
                                    "className": "text-[11px] font-bold text-amber-800 uppercase tracking-wider block"
                                },
                                "Historial de Devoluciones Auditadas:",
                            ),
                            html.ul(
                                {"className": "space-y-1.5 pl-2"},
                                *[
                                    html.li(
                                        {
                                            "className": "p-2 rounded bg-white/80 border border-amber-200/70 space-y-0.5",
                                        },
                                        html.div(
                                            {
                                                "className": "flex items-center justify-between text-[10px] text-slate-400 font-mono"
                                            },
                                            html.span(
                                                f"{tr.estadoOrigen.value} → {tr.estadoDestino.value}"
                                            ),
                                            html.span(tr.fechaHora),
                                        ),
                                        html.p(
                                            {
                                                "className": "text-xs text-slate-700 italic"
                                            },
                                            f'"{tr.comentario.obtenerValor()}"',
                                        ),
                                    )
                                    for tr in transicionesConMotivo
                                ],
                            ),
                        )
                        if estaAbierto and transicionesConMotivo
                        else html.div()
                    ),
                )
            )

    seccionCuellosBotella = html.div(
        {
            "id": "seccion-cuellos-botella",
            "className": "p-6 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-4",
        },
        html.div(
            {"className": "flex items-center justify-between"},
            html.div(
                {"className": "space-y-0.5"},
                html.h3(
                    {
                        "className": "text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-2"
                    },
                    html.span("⚠️"),
                    html.span("Auditoría de Cuellos de Botella"),
                ),
                html.p(
                    {"className": "text-xs text-slate-500"},
                    "Tareas activas con devoluciones registradas ordenadas descendentemente por reincidencia.",
                ),
            ),
            html.span(
                {
                    "id": "total-cuellos-botella-badge",
                    "className": (
                        "text-xs font-bold px-2 py-0.5 rounded "
                        + (
                            "bg-amber-100 text-amber-800"
                            if cuellosDeBotella
                            else "bg-slate-100 text-slate-500"
                        )
                    ),
                },
                f"{len(cuellosDeBotella)} tareas",
            ),
        ),
        html.div(
            {"className": "space-y-3"},
            (
                filasCuellos
                if filasCuellos
                else html.div(
                    {
                        "id": "sin-cuellos-botella",
                        "className": "p-6 rounded-xl bg-emerald-50/60 border border-emerald-200/60 text-center space-y-1",
                    },
                    html.span({"className": "text-xl"}, "✓"),
                    html.p(
                        {"className": "text-xs font-bold text-emerald-900"},
                        "Flujo Continuo Sin Cuellos de Botella",
                    ),
                    html.p(
                        {"className": "text-[11px] text-emerald-700"},
                        "No se registran tareas con retrocesos o devoluciones en este proyecto.",
                    ),
                )
            ),
        ),
    )

    # E. Sub-panel de Filtros Analíticos y Consulta Avanzada (EARS-07.4)
    filasTablaTareas = []
    for t in tareasOrdenadas:
        nombreResp = "Sin asignar"
        if t.cedulaResponsable.esAlguno():
            ced = t.cedulaResponsable.obtenerValor()
            mb = next((m for m in proyecto.integrantes if m.cedula == ced), None)
            if mb:
                nombreResp = mb.nombre

        fechaTxt = (
            t.fechaObjetivo.obtenerValor()
            if t.fechaObjetivo.esAlguno()
            else "Sin fecha"
        )
        estaVencida = bool(
            t.fechaObjetivo.esAlguno()
            and t.fechaObjetivo.obtenerValor() < fechaHoy
            and t.estado != EstadoKanban.TERMINADA
        )

        filasTablaTareas.append(
            html.tr(
                {
                    "id": f"fila-tarea-analitica-{t.idTarea}",
                    "className": "border-b border-slate-100 hover:bg-slate-50/60 transition-colors text-xs",
                },
                html.td(
                    {"className": "py-2.5 px-3 font-mono font-bold text-slate-700"},
                    t.idTarea,
                ),
                html.td(
                    {
                        "className": "py-2.5 px-3 font-semibold text-slate-800 max-w-xs truncate"
                    },
                    t.titulo,
                ),
                html.td(
                    {"className": "py-2.5 px-3"},
                    html.span(
                        {"className": obtenerClaseEstadoKanban(t.estado)},
                        t.estado.value,
                    ),
                ),
                html.td(
                    {"className": "py-2.5 px-3"},
                    html.span(
                        {"className": obtenerClasePrioridad(t.prioridad)},
                        t.prioridad.value,
                    ),
                ),
                html.td(
                    {"className": "py-2.5 px-3 text-slate-600 truncate max-w-[120px]"},
                    nombreResp,
                ),
                html.td(
                    {"className": "py-2.5 px-3 font-mono"},
                    html.span(
                        {
                            "className": "text-rose-600 font-bold"
                            if estaVencida
                            else "text-slate-500",
                        },
                        fechaTxt + (" (Vencida)" if estaVencida else ""),
                    ),
                ),
                html.td(
                    {"className": "py-2.5 px-3 text-center"},
                    (
                        html.span(
                            {
                                "className": "px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200"
                            },
                            f"↩ {t.contadorRegresos}",
                        )
                        if t.contadorRegresos > 0
                        else html.span({"className": "text-slate-300"}, "-")
                    ),
                ),
                html.td(
                    {"className": "py-2.5 px-3 text-right"},
                    (
                        html.span(
                            {
                                "className": "text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded"
                            },
                            "Activa",
                        )
                        if t.activo
                        else html.span(
                            {
                                "className": "text-[10px] font-semibold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded"
                            },
                            "Descartada",
                        )
                    ),
                ),
            )
        )

    seccionFiltrosYTabla = html.div(
        {
            "id": "panel-filtros-analiticos",
            "className": "p-6 rounded-2xl bg-white border border-slate-200/80 shadow-sm space-y-5",
        },
        html.div(
            {
                "className": "flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            },
            html.div(
                {"className": "space-y-0.5"},
                html.h3(
                    {
                        "className": "text-sm font-bold text-slate-900 uppercase tracking-wider"
                    },
                    "Consulta y Filtros Analíticos Avanzados",
                ),
                html.p(
                    {"className": "text-xs text-slate-500"},
                    "Filtrado declarativo combinado fuera del tablero operativo con ordenamiento dinámico.",
                ),
            ),
            # Ordenamiento
            html.div(
                {"className": "flex items-center space-x-2"},
                html.label(
                    {"className": "text-xs font-semibold text-slate-500"},
                    "Ordenar por:",
                ),
                html.select(
                    {
                        "id": "select-ordenamiento",
                        "value": criterioOrden,
                        "onChange": lambda e: setCriterioOrden(e["target"]["value"]),
                        "className": f"{INPUT_TEXTO} py-1 text-xs font-medium w-auto",
                    },
                    html.option({"value": "FECHA"}, "Fecha Objetivo"),
                    html.option({"value": "PRIORIDAD"}, "Prioridad"),
                ),
            ),
        ),
        # Barra de Filtros
        html.div(
            {
                "className": "grid grid-cols-1 sm:grid-cols-3 gap-3 p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 text-xs"
            },
            # Filtro Estado
            html.div(
                {"className": "space-y-1"},
                html.label(
                    {"className": "font-bold text-slate-600 block text-[11px]"},
                    "Estado Kanban",
                ),
                html.select(
                    {
                        "id": "filtro-estado",
                        "value": filtroEstado,
                        "onChange": lambda e: setFiltroEstado(e["target"]["value"]),
                        "className": f"{INPUT_TEXTO} py-1.5 text-xs",
                    },
                    html.option({"value": ""}, "Todos los estados"),
                    *[
                        html.option({"value": est.value}, est.value)
                        for est in EstadoKanban
                    ],
                    html.option({"value": "DESCARTADAS"}, "Descartadas / Inactivas"),
                ),
            ),
            # Filtro Responsable
            html.div(
                {"className": "space-y-1"},
                html.label(
                    {"className": "font-bold text-slate-600 block text-[11px]"},
                    "Responsable",
                ),
                html.select(
                    {
                        "id": "filtro-responsable",
                        "value": filtroResponsable,
                        "onChange": lambda e: setFiltroResponsable(
                            e["target"]["value"]
                        ),
                        "className": f"{INPUT_TEXTO} py-1.5 text-xs",
                    },
                    html.option({"value": ""}, "Todos los responsables"),
                    *[
                        html.option({"value": m.cedula}, m.nombre)
                        for m in proyecto.integrantes
                    ],
                ),
            ),
            # Filtro Prioridad
            html.div(
                {"className": "space-y-1"},
                html.label(
                    {"className": "font-bold text-slate-600 block text-[11px]"},
                    "Prioridad",
                ),
                html.select(
                    {
                        "id": "filtro-prioridad",
                        "value": filtroPrioridad,
                        "onChange": lambda e: setFiltroPrioridad(e["target"]["value"]),
                        "className": f"{INPUT_TEXTO} py-1.5 text-xs",
                    },
                    html.option({"value": ""}, "Todas las prioridades"),
                    *[html.option({"value": p.value}, p.value) for p in PrioridadTarea],
                ),
            ),
        ),
        # Checkboxes de Criterios Especiales
        html.div(
            {
                "className": "flex flex-wrap items-center gap-6 text-xs font-medium text-slate-700"
            },
            html.label(
                {"className": "flex items-center space-x-2 cursor-pointer"},
                html.input(
                    {
                        "id": "checkbox-solo-vencidas",
                        "type": "checkbox",
                        "checked": soloVencidas,
                        "onChange": lambda e: setSoloVencidas(not soloVencidas),
                        "className": "w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500",
                    }
                ),
                html.span("Solo tareas vencidas"),
            ),
            html.span(
                {
                    "id": "conteo-resultados-filtrados",
                    "className": "ml-auto text-slate-400 font-mono text-[11px]",
                },
                f"{len(tareasOrdenadas)} coincidencia(s)",
            ),
        ),
        # Tabla de Resultados
        html.div(
            {
                "className": "overflow-x-auto border border-slate-200/80 rounded-xl",
            },
            html.table(
                {
                    "id": "tabla-tareas-analitica",
                    "className": "w-full text-left border-collapse",
                },
                html.thead(
                    {
                        "className": "bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider",
                    },
                    html.tr(
                        {},
                        html.th({"className": "py-2.5 px-3"}, "ID"),
                        html.th({"className": "py-2.5 px-3"}, "Título"),
                        html.th({"className": "py-2.5 px-3"}, "Estado"),
                        html.th({"className": "py-2.5 px-3"}, "Prioridad"),
                        html.th({"className": "py-2.5 px-3"}, "Responsable"),
                        html.th({"className": "py-2.5 px-3"}, "Fecha Obj"),
                        html.th({"className": "py-2.5 px-3 text-center"}, "Regresos"),
                        html.th({"className": "py-2.5 px-3 text-right"}, "Condición"),
                    ),
                ),
                html.tbody(
                    {},
                    (
                        filasTablaTareas
                        if filasTablaTareas
                        else html.tr(
                            {},
                            html.td(
                                {
                                    "colSpan": 8,
                                    "className": "py-8 text-center text-xs text-slate-400 italic",
                                },
                                "No hay tareas que coincidan con los filtros aplicados.",
                            ),
                        )
                    ),
                ),
            ),
        ),
    )

    # -------------------------------------------------------------------------
    # 5. Ensamblado Estructural de la Pantalla de Métricas
    # -------------------------------------------------------------------------
    return html.main(
        {
            "id": "vista-metricas-contenedor",
            "className": "flex-1 flex flex-col overflow-y-auto bg-slate-50 p-6 max-w-7xl w-full mx-auto space-y-6 animate-in fade-in duration-150",
        },
        # Encabezado Superior con Retorno al Workspace
        html.header(
            {
                "id": "encabezado-vista-metricas",
                "className": "flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200",
            },
            html.div(
                {"className": "space-y-1"},
                html.div(
                    {"className": "flex items-center space-x-2 text-xs text-slate-400"},
                    html.span(proyecto.nombre),
                    html.span("/"),
                    html.span(
                        {"className": "font-semibold text-indigo-600"},
                        "Métricas y Analítica",
                    ),
                ),
                html.h1(
                    {
                        "id": "titulo-vista-metricas",
                        "className": "text-2xl font-extrabold text-slate-900 tracking-tight",
                    },
                    f"Métricas — {proyecto.nombre}",
                ),
                html.p(
                    {"className": "text-xs text-slate-500 leading-relaxed"},
                    "Supervisión ejecutiva de avance EDT, auditoría de cuellos de botella y balance de carga.",
                ),
            ),
            html.button(
                {
                    "id": "btn-volver-workspace-desde-metricas",
                    "type": "button",
                    "onClick": lambda e: alVolverWorkspace(),
                    "className": f"{BOTON_PRIMARIO} py-2 px-4 text-xs font-semibold shadow-sm flex items-center space-x-1.5",
                },
                html.span("←"),
                html.span("Volver al Workspace"),
            ),
        ),
        # Grilla de Métricas Principales (KPIs)
        kpis,
        # Dos Columnas Principales: Paquetes EDT vs Cuellos de Botella / Equipo
        html.div(
            {
                "className": "grid grid-cols-1 lg:grid-cols-2 gap-6",
            },
            seccionPaquetes,
            html.div(
                {"className": "space-y-6"},
                seccionCuellosBotella,
                seccionEquipo,
            ),
        ),
        # Panel Inferior: Filtros Analíticos y Consulta Avanzada
        seccionFiltrosYTabla,
    )
