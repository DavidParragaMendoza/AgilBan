# ruff: noqa: N999
"""Componente de tarjeta visual de tarea en el tablero Kanban.

Implementa los requerimientos RF-04 y RF-06 (EARS-04.1 a EARS-04.4, EARS-06.1):
- Proyección de identificador correlativo visible (TAR-NNN).
- Título con truncado elegante hasta 120 caracteres.
- Badge cromático de prioridad (Baja, Media, Alta, Crítica).
- Nombre del integrante responsable o indicación 'Sin asignar'.
- Fecha objetivo con distintivo rojo 'Vencida' si ha caducado, sin bloquear acciones.
- Contador de regresos visible si es mayor a cero.
- Acciones de transición permitidas según el estado actual:
  * Pendiente: avanzar a En progreso (sin acción de devolución).
  * En progreso: avanzar a En revisión o solicitar Devolver.
  * En revisión: avanzar a Terminada o solicitar Devolver.
  * Terminada: únicamente solicitar Devolver (sin avance hacia adelante).
  * Prohibido cualquier selector o menú de destinos manuales.
- Apertura del Side Drawer al hacer clic sobre el cuerpo de la tarjeta.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from reactpy import component, html
from reactpy.types import VdomDict

from app.core.kanban import destinoRetroceso
from app.domain.catalogos import EstadoKanban
from app.domain.modelos import Integrante, Tarea
from app.ui.web.estilos import (
    BADGE_TAREA_VENCIDA,
    TARJETA_KANBAN,
    obtenerClasePrioridad,
)


def _obtenerSiguienteEstado(estadoActual: EstadoKanban) -> EstadoKanban | None:
    """Retorna el único siguiente estado válido hacia adelante según el flujo Kanban."""
    match estadoActual:
        case EstadoKanban.PENDIENTE:
            return EstadoKanban.EN_PROGRESO
        case EstadoKanban.EN_PROGRESO:
            return EstadoKanban.EN_REVISION
        case EstadoKanban.EN_REVISION:
            return EstadoKanban.TERMINADA
        case EstadoKanban.TERMINADA:
            return None


def _esFechaVencida(fechaStr: str) -> bool:
    """Determina si la fecha objetivo (YYYY-MM-DD) es estrictamente anterior a hoy."""
    if not fechaStr or not fechaStr.strip():
        return False
    hoy = datetime.now().strftime("%Y-%m-%d")
    return fechaStr.strip() < hoy


@component
def tarjetaTarea(
    tarea: Tarea,
    integrantes: tuple[Integrante, ...],
    alSeleccionarTarea: Callable[[Tarea], None],
    alAvanzar: Callable[[Tarea, EstadoKanban], None],
    alSolicitarDevolucion: Callable[[Tarea], None],
) -> VdomDict:
    """Renderiza una tarjeta individual en el tablero Kanban con sus acciones permitidas."""
    # 1. Resolución del responsable asignado
    nombreResponsable = "Sin asignar"
    inicialesResponsable = "SA"
    if tarea.cedulaResponsable.esAlguno():
        cedula = tarea.cedulaResponsable.obtenerValor()
        miembro = next((m for m in integrantes if m.cedula == cedula), None)
        if miembro is not None:
            nombreResponsable = miembro.nombre
            inicialesResponsable = "".join(
                p[0].upper() for p in miembro.nombre.split() if p
            )[:2]

    # 2. Evaluación de fecha objetivo y vencimiento
    tieneFecha = tarea.fechaObjetivo.esAlguno()
    fechaTexto = tarea.fechaObjetivo.obtenerValor() if tieneFecha else ""
    estaVencida = _esFechaVencida(fechaTexto) if tieneFecha else False

    # 3. Transiciones permitidas
    siguienteEstado = _obtenerSiguienteEstado(tarea.estado)
    opcionRegreso = destinoRetroceso(tarea.estado)
    permiteDevolucion = opcionRegreso.esAlguno()

    # Manejadores de clic seguros (evitan propagación a selección de tarjeta)
    def manejarAvanzar(evento: dict) -> None:
        if siguienteEstado is not None:
            alAvanzar(tarea, siguienteEstado)

    def manejarDevolver(evento: dict) -> None:
        if permiteDevolucion:
            alSolicitarDevolucion(tarea)

    def manejarClicTarjeta(evento: dict) -> None:
        alSeleccionarTarea(tarea)

    # 4. Construcción de botones de acción
    botonesAccion = []

    # Botón Devolver (solo en En progreso, En revisión y Terminada)
    if permiteDevolucion:
        botonesAccion.append(
            html.button(
                {
                    "id": f"btn-devolver-tarea-{tarea.idTarea}",
                    "type": "button",
                    "onClick": manejarDevolver,
                    "className": (
                        "px-2 py-1 rounded text-[11px] font-semibold bg-amber-50 text-amber-800 "
                        "border border-amber-200 hover:bg-amber-100 active:bg-amber-200 "
                        "transition-colors flex items-center space-x-1 focus:outline-none"
                    ),
                    "title": f"Solicitar devolución hacia {opcionRegreso.obtenerValor().value}",
                },
                html.span("↩"),
                html.span("Devolver"),
            )
        )

    # Botón Avanzar (en Pendiente, En progreso y En revisión)
    if siguienteEstado is not None:
        etiquetaAvanzar = (
            "En progreso →"
            if siguienteEstado == EstadoKanban.EN_PROGRESO
            else (
                "En revisión →"
                if siguienteEstado == EstadoKanban.EN_REVISION
                else "Terminar ✓"
            )
        )
        botonesAccion.append(
            html.button(
                {
                    "id": f"btn-avanzar-tarea-{tarea.idTarea}",
                    "type": "button",
                    "onClick": manejarAvanzar,
                    "className": (
                        "px-2.5 py-1 rounded text-[11px] font-semibold bg-indigo-50 text-indigo-700 "
                        "border border-indigo-200 hover:bg-indigo-100 active:bg-indigo-200 "
                        "transition-colors flex items-center space-x-1 focus:outline-none ml-auto"
                    ),
                    "title": f"Avanzar al siguiente estado: {siguienteEstado.value}",
                },
                html.span(etiquetaAvanzar),
            )
        )

    # 5. Renderizado final del artículo VDOM
    return html.article(
        {
            "id": f"tarjeta-tarea-{tarea.idTarea}",
            "className": (
                f"{TARJETA_KANBAN} border border-slate-200 hover:border-indigo-300 "
                "bg-white rounded-xl p-3.5 shadow-sm hover:shadow-md transition-all "
                "cursor-pointer space-y-2.5 group relative"
            ),
        },
        # Fila Superior: ID, Prioridad y Regresos
        html.div(
            {
                "className": "flex items-center justify-between gap-1.5",
                "onClick": manejarClicTarjeta,
            },
            html.div(
                {"className": "flex items-center space-x-1.5"},
                html.span(
                    {
                        "id": f"id-tarea-{tarea.idTarea}",
                        "className": "font-mono text-[11px] font-bold text-slate-400 group-hover:text-indigo-600 transition-colors",
                    },
                    tarea.idTarea,
                ),
                (
                    html.span(
                        {
                            "id": f"contador-regresos-{tarea.idTarea}",
                            "className": (
                                "inline-flex items-center px-1.5 py-0.2 rounded-full text-[10px] "
                                "font-bold bg-amber-50 text-amber-700 border border-amber-200"
                            ),
                            "title": f"Esta tarea ha retrocedido {tarea.contadorRegresos} vez/veces",
                        },
                        f"↩ {tarea.contadorRegresos}",
                    )
                    if tarea.contadorRegresos > 0
                    else html.span()
                ),
            ),
            html.span(
                {
                    "id": f"badge-prioridad-{tarea.idTarea}",
                    "className": f"{obtenerClasePrioridad(tarea.prioridad)} text-[10px] py-0.5",
                },
                tarea.prioridad.value,
            ),
        ),
        # Título de la Tarea
        html.h4(
            {
                "id": f"titulo-tarea-{tarea.idTarea}",
                "onClick": manejarClicTarjeta,
                "className": (
                    "text-xs font-semibold text-slate-800 line-clamp-2 leading-relaxed "
                    "group-hover:text-indigo-900 transition-colors"
                ),
                "title": tarea.titulo,
            },
            tarea.titulo,
        ),
        # Metadatos: Responsable y Fecha Objetivo
        html.div(
            {
                "className": "flex items-center justify-between gap-2 pt-1 text-[11px] text-slate-500",
                "onClick": manejarClicTarjeta,
            },
            # Responsable
            html.div(
                {
                    "id": f"responsable-tarea-{tarea.idTarea}",
                    "className": "flex items-center space-x-1.5 min-w-0",
                    "title": f"Responsable: {nombreResponsable}",
                },
                html.div(
                    {
                        "className": (
                            "w-5 h-5 rounded-full bg-slate-100 text-slate-600 text-[9px] "
                            "font-bold flex items-center justify-center flex-shrink-0"
                        ),
                    },
                    inicialesResponsable,
                ),
                html.span(
                    {"className": "truncate max-w-[100px]"},
                    nombreResponsable,
                ),
            ),
            # Fecha Objetivo / Vencimiento
            html.div(
                {
                    "id": f"fecha-tarea-{tarea.idTarea}",
                    "className": "flex items-center space-x-1 flex-shrink-0",
                },
                (
                    html.div(
                        {"className": "flex items-center space-x-1"},
                        (
                            html.span(
                                {
                                    "id": f"badge-vencida-{tarea.idTarea}",
                                    "className": f"{BADGE_TAREA_VENCIDA} text-[9px] py-0.2 px-1",
                                    "title": "La fecha objetivo ha caducado",
                                },
                                "Vencida",
                            )
                            if estaVencida
                            else html.span()
                        ),
                        html.span(
                            {
                                "className": (
                                    "font-mono text-[10px] "
                                    + (
                                        "text-rose-600 font-semibold"
                                        if estaVencida
                                        else "text-slate-400"
                                    )
                                ),
                            },
                            fechaTexto,
                        ),
                    )
                    if tieneFecha
                    else html.span(
                        {"className": "text-[10px] text-slate-300 italic"},
                        "Sin fecha",
                    )
                ),
            ),
        ),
        # Fila de Acciones de Transición
        html.div(
            {
                "id": f"acciones-tarea-{tarea.idTarea}",
                "className": "flex items-center pt-2 mt-1 border-t border-slate-100 space-x-2",
            },
            *botonesAccion,
        ),
    )
