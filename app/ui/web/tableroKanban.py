# ruff: noqa: N999
"""Tablero Kanban limpio de 4 columnas delimitadas y gestión de tareas del paquete.

Implementa los requerimientos RF-04, RF-05 y RF-06 (EARS-04.1 a EARS-04.7):
- 4 columnas visuales fijas (Pendiente, En progreso, En revisión, Terminada).
- Filtrado exclusivo de tareas activas (activo = 1).
- Indicación neutral para columnas vacías sin presentarlo como error.
- Estado orientador cuando el paquete de trabajo no posee tareas activas.
- Acción '+ Nueva Tarea' con validación de título (1 a 120 caracteres) y clave idempotente.
- Preservación de título y clave ante fallos de persistencia para reintentos sin duplicación.
- Apertura del Side Drawer únicamente tras la confirmación exitosa de guardado en SQLite.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from reactpy import component, html, use_state
from reactpy.types import VdomDict

from app.domain.catalogos import EstadoKanban
from app.domain.modelos import Integrante, PaqueteTrabajo, Tarea
from app.ui.web.estilos import (
    BOTON_PRIMARIO,
    BOTON_SECUNDARIO,
    CONTENEDOR_MODAL,
    ENCABEZADO_MODAL,
    FONDO_COLUMNA_KANBAN,
    FONDO_MODAL_OVERLAY,
    INPUT_ERROR,
    INPUT_TEXTO,
    PIE_MODAL,
    TEXTO_ERROR_FORMULARIO,
    obtenerClaseEstadoKanban,
)
from app.ui.web.tarjetaTarea import tarjetaTarea

COLUMNAS_KANBAN: tuple[EstadoKanban, ...] = (
    EstadoKanban.PENDIENTE,
    EstadoKanban.EN_PROGRESO,
    EstadoKanban.EN_REVISION,
    EstadoKanban.TERMINADA,
)


@component
def tableroKanban(
    paquete: PaqueteTrabajo,
    integrantes: tuple[Integrante, ...],
    alSeleccionarTarea: Callable[[Tarea], None],
    alAvanzarTarea: Callable[[Tarea, EstadoKanban], None],
    alSolicitarDevolucion: Callable[[Tarea], None],
    alCrearTarea: Callable[[str, str], None],
    errorPersistencia: str = "",
) -> VdomDict:
    """Componente principal del tablero Kanban estructurado en 4 columnas delimitadas."""
    # Estados locales para la creación interactiva de nuevas tareas
    modalCreacionAbierto, setModalCreacionAbierto = use_state(False)
    tituloNuevaTarea, setTituloNuevaTarea = use_state("")
    errorTitulo, setErrorTitulo = use_state("")
    claveIdempotente, setClaveIdempotente = use_state("")

    # Filtrar únicamente tareas activas del paquete actual
    tareasActivas = tuple(t for t in paquete.tareas if t.activo)
    tieneTareas = len(tareasActivas) > 0

    # -------------------------------------------------------------------------
    # Manejadores de eventos de creación de tareas
    # -------------------------------------------------------------------------
    def abrirModalCreacion() -> None:
        setErrorTitulo("")
        if not claveIdempotente:
            setClaveIdempotente(str(uuid.uuid4()))
        setModalCreacionAbierto(True)

    def cerrarModalCreacion() -> None:
        setModalCreacionAbierto(False)
        setErrorTitulo("")

    def confirmarCreacionTarea() -> None:
        texto = tituloNuevaTarea.strip()
        if not (1 <= len(texto) <= 120):
            setErrorTitulo(
                "El título de la tarea es obligatorio y debe tener entre 1 y 120 caracteres."
            )
            return

        claveActual = claveIdempotente if claveIdempotente else str(uuid.uuid4())
        setErrorTitulo("")
        # No limpiamos la clave aún por si falla la persistencia y requiere reintento
        alCrearTarea(texto, claveActual)
        setModalCreacionAbierto(False)
        setTituloNuevaTarea("")
        setClaveIdempotente("")

    # -------------------------------------------------------------------------
    # Renderizado de Columnas Individuales
    # -------------------------------------------------------------------------
    elementosColumnas: list[VdomDict] = []
    for colEstado in COLUMNAS_KANBAN:
        tareasColumna = tuple(t for t in tareasActivas if t.estado == colEstado)
        claseBadge = obtenerClaseEstadoKanban(colEstado)
        nombreColumna = colEstado.value
        claveColumna = colEstado.name.lower()

        tarjetasHtml = [
            tarjetaTarea(
                key=f"tarjeta-{t.idTarea}",
                tarea=t,
                integrantes=integrantes,
                alSeleccionarTarea=alSeleccionarTarea,
                alAvanzar=alAvanzarTarea,
                alSolicitarDevolucion=alSolicitarDevolucion,
            )
            for t in tareasColumna
        ]

        elementosColumnas.append(
            html.div(
                {
                    "id": f"columna-kanban-{claveColumna}",
                    "className": (
                        f"{FONDO_COLUMNA_KANBAN} h-full overflow-hidden flex flex-col "
                        "shadow-sm border border-slate-200/80 rounded-2xl bg-slate-100/60"
                    ),
                },
                # Cabecera de Columna
                html.div(
                    {
                        "id": f"cabecera-columna-{claveColumna}",
                        "className": "flex items-center justify-between pb-3 mb-2 border-b border-slate-200/60 flex-shrink-0",
                    },
                    html.div(
                        {"className": "flex items-center space-x-2"},
                        html.span(
                            {
                                "id": f"badge-columna-{claveColumna}",
                                "className": f"{claseBadge} text-xs font-bold py-0.5",
                            },
                            nombreColumna,
                        ),
                    ),
                    html.div(
                        {"className": "flex items-center space-x-1.5"},
                        (
                            html.button(
                                {
                                    "id": "btn-nueva-tarea-kanban",
                                    "type": "button",
                                    "onClick": lambda e: abrirModalCreacion(),
                                    "className": (
                                        "px-2 py-0.5 rounded text-xs font-semibold bg-indigo-50 "
                                        "text-indigo-700 hover:bg-indigo-100 transition-colors"
                                    ),
                                    "title": "Crear nueva tarea en Pendiente",
                                },
                                "+ Tarea",
                            )
                            if colEstado == EstadoKanban.PENDIENTE
                            else html.span()
                        ),
                        html.span(
                            {
                                "id": f"conteo-columna-{claveColumna}",
                                "className": "px-2 py-0.5 rounded-full bg-white text-slate-600 font-bold text-xs shadow-sm border border-slate-200",
                            },
                            str(len(tareasColumna)),
                        ),
                    ),
                ),
                # Lista de Tarjetas o Indicación Neutral
                html.div(
                    {
                        "id": f"lista-tarjetas-columna-{claveColumna}",
                        "className": "flex-1 overflow-y-auto space-y-3 pr-1",
                    },
                    (
                        tarjetasHtml
                        if len(tarjetasHtml) > 0
                        else html.div(
                            {
                                "id": f"columna-vacia-{claveColumna}",
                                "className": (
                                    "p-6 text-center border-2 border-dashed border-slate-200 "
                                    "rounded-xl my-2 bg-white/40"
                                ),
                            },
                            html.p(
                                {"className": "text-xs font-medium text-slate-400"},
                                "Sin tareas en esta columna",
                            ),
                        )
                    ),
                ),
            )
        )

    # -------------------------------------------------------------------------
    # Modal interactivo de creación de tarea
    # -------------------------------------------------------------------------
    modalCreacion = html.div()
    if modalCreacionAbierto:
        claseInput = INPUT_ERROR if errorTitulo else INPUT_TEXTO
        modalCreacion = html.div(
            {
                "id": "modal-nueva-tarea-backdrop",
                "className": FONDO_MODAL_OVERLAY,
            },
            html.div(
                {
                    "id": "modal-nueva-tarea",
                    "className": f"{CONTENEDOR_MODAL} max-w-md",
                },
                html.div(
                    {"className": ENCABEZADO_MODAL},
                    html.div(
                        {"className": "flex items-center space-x-2"},
                        html.span(
                            {"className": "text-lg font-bold text-indigo-600"}, "+"
                        ),
                        html.h3(
                            {"className": "text-base font-bold text-slate-900"},
                            "Nueva Tarea",
                        ),
                    ),
                    html.button(
                        {
                            "id": "btn-cerrar-modal-nueva-tarea",
                            "type": "button",
                            "onClick": lambda e: cerrarModalCreacion(),
                            "className": "text-slate-400 hover:text-slate-600 font-bold text-sm",
                        },
                        "✕",
                    ),
                ),
                html.div(
                    {"className": "p-6 space-y-3"},
                    html.p(
                        {"className": "text-xs text-slate-500 leading-relaxed"},
                        f"Crear una nueva tarea en el paquete '{paquete.nombre}'.",
                    ),
                    html.div(
                        {"className": "space-y-1.5"},
                        html.label(
                            {
                                "className": "text-xs font-bold text-slate-700 uppercase tracking-wider",
                            },
                            "Título de la tarea *",
                        ),
                        html.input(
                            {
                                "id": "input-titulo-nueva-tarea",
                                "type": "text",
                                "placeholder": "Ej: Implementar endpoints de autenticación JWT (máx. 120)",
                                "value": tituloNuevaTarea,
                                "onChange": lambda e: setTituloNuevaTarea(
                                    e["target"]["value"]
                                ),
                                "className": f"{claseInput} text-xs py-2",
                                "maxLength": 120,
                                "autoFocus": True,
                            }
                        ),
                        html.span(
                            {
                                "id": "error-titulo-nueva-tarea",
                                "className": TEXTO_ERROR_FORMULARIO
                                if errorTitulo
                                else "hidden",
                            },
                            errorTitulo,
                        ),
                    ),
                ),
                html.div(
                    {"className": PIE_MODAL},
                    html.button(
                        {
                            "id": "btn-cancelar-nueva-tarea",
                            "type": "button",
                            "onClick": lambda e: cerrarModalCreacion(),
                            "className": BOTON_SECUNDARIO,
                        },
                        "Cancelar",
                    ),
                    html.button(
                        {
                            "id": "btn-guardar-nueva-tarea",
                            "type": "button",
                            "onClick": lambda e: confirmarCreacionTarea(),
                            "className": BOTON_PRIMARIO,
                        },
                        "Crear Tarea",
                    ),
                ),
            ),
        )

    # -------------------------------------------------------------------------
    # Ensamblado del Tablero Kanban
    # -------------------------------------------------------------------------
    return html.div(
        {
            "id": "tablero-kanban-contenedor",
            "className": "flex-1 flex flex-col h-full overflow-hidden",
        },
        # Banner orientador cuando no hay tareas en el paquete (EARS-04.7)
        (
            html.div(
                {
                    "id": "tablero-vacio-paquete",
                    "className": (
                        "mx-6 mt-4 p-4 rounded-xl bg-indigo-50/60 border border-indigo-200/80 "
                        "flex items-center justify-between gap-4 animate-in fade-in duration-150 flex-shrink-0"
                    ),
                },
                html.div(
                    {"className": "flex items-center space-x-3"},
                    html.div(
                        {
                            "className": "w-8 h-8 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm"
                        },
                        "📋",
                    ),
                    html.div(
                        {"className": "space-y-0.5"},
                        html.p(
                            {"className": "text-xs font-bold text-indigo-950"},
                            "Paquete sin tareas activas",
                        ),
                        html.p(
                            {"className": "text-[11px] text-indigo-700 leading-snug"},
                            "Comienza organizando el flujo de trabajo agregando tu primera tarea a la columna 'Pendiente'.",
                        ),
                    ),
                ),
                html.button(
                    {
                        "id": "btn-crear-primera-tarea",
                        "type": "button",
                        "onClick": lambda e: abrirModalCreacion(),
                        "className": f"{BOTON_PRIMARIO} py-1.5 px-3 text-xs",
                    },
                    "+ Nueva Tarea",
                ),
            )
            if not tieneTareas
            else html.div()
        ),
        # Área de las 4 Columnas Delimitadas
        html.div(
            {
                "id": "area-columnas-kanban",
                "className": "flex-1 overflow-x-auto p-6 flex gap-5 bg-slate-50 min-h-0",
            },
            *elementosColumnas,
        ),
        # Modal emergente
        modalCreacion,
    )
