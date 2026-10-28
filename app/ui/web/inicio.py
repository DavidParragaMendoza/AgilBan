"""Pantalla de inicio, explorador de catalogo y busqueda local estilo NotebookLM.

Implementa RF-01 y RF-08:
- Bienvenida minimalista orientadora cuando el catalogo esta vacio (EARS-01.1).
- Cuadricula (grid) interactiva de tarjetas con porcentaje de avance y paquetes (EARS-01.2).
- Carga instantanea del Workspace al seleccionar tarjeta sin recargar pagina (EARS-01.3).
- Apertura del dialogo modal guiado de creacion de proyecto (EARS-01.4).
- Filtro local por nombre insensible a mayusculas/minusculas y estado diferenciado de busqueda sin resultados (EARS-01.5).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from reactpy import component, html
from reactpy.types import VdomDict

from app.core.metricas import calcularAvanceGlobal
from app.domain.modelos import Proyecto
from app.ui.web.estilos import (
    BORDE_SUAVE,
    BOTON_PRIMARIO,
    BOTON_SECUNDARIO,
    INPUT_TEXTO,
    SUBTITULO_PANTALLA,
    TARJETA_PROYECTO,
    TITULO_PANTALLA,
    TITULO_SECCION,
    TITULO_TARJETA,
)


def filtrarProyectosPorNombre(
    proyectos: tuple[Proyecto, ...], texto: str
) -> tuple[Proyecto, ...]:
    """Filtra puramente los proyectos cuyo nombre contenga la cadena dada, sin distinguir mayusculas."""
    termino = texto.strip().lower()
    if not termino:
        return proyectos
    return tuple(p for p in proyectos if termino in p.nombre.lower())


def renderizarTarjetaProyecto(
    proyecto: Proyecto,
    alSeleccionarProyecto: Callable[[str], None],
    alEliminarProyecto: Callable[[str], None] | None = None,
) -> VdomDict:
    """Renderiza puramente la tarjeta interactiva de un proyecto con avance y metadatos."""
    todasLasTareas = tuple(t for paq in proyecto.paquetes for t in paq.tareas)
    tareasActivas = tuple(t for t in todasLasTareas if t.activo)
    avance = calcularAvanceGlobal(todasLasTareas)

    colorBarra = "bg-emerald-500" if avance >= 100.0 else "bg-indigo-600"

    return html.div(
        {
            "id": f"tarjeta-proyecto-{proyecto.idProyecto}",
            "onClick": lambda e, pid=proyecto.idProyecto: alSeleccionarProyecto(pid),
            "className": f"{TARJETA_PROYECTO} min-h-[200px] group",
        },
        html.div(
            {"className": "space-y-3"},
            html.div(
                {"className": "flex items-start justify-between gap-2"},
                html.span(
                    {
                        "className": (
                            "px-2.5 py-0.5 rounded-full text-xs font-medium "
                            "bg-indigo-50 text-indigo-700 border border-indigo-100"
                        )
                    },
                    proyecto.tipo.value,
                ),
                html.div(
                    {"className": "flex items-center space-x-2"},
                    html.span(
                        {
                            "className": "text-xs font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded"
                        },
                        f"{avance:.1f}%",
                    ),
                    (
                        html.button(
                            {
                                "id": f"btn-eliminar-proyecto-{proyecto.idProyecto}",
                                "onClick": lambda e, pid=proyecto.idProyecto: (
                                    alEliminarProyecto(pid)
                                ),
                                "className": (
                                    "p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 "
                                    "transition-colors text-xs"
                                ),
                                "title": "Eliminar proyecto",
                            },
                            "🗑️",
                        )
                        if alEliminarProyecto is not None
                        else html.span()
                    ),
                ),
            ),
            html.h3(
                {
                    "className": f"{TITULO_TARJETA} text-base group-hover:text-indigo-600 transition-colors"
                },
                proyecto.nombre,
            ),
            html.div(
                {"className": "flex items-center space-x-4 text-xs text-slate-500"},
                html.span(
                    {"className": "flex items-center space-x-1"},
                    html.span("📦"),
                    html.span(f"{len(proyecto.paquetes)} paquetes"),
                ),
                html.span(
                    {"className": "flex items-center space-x-1"},
                    html.span("👥"),
                    html.span(f"{len(proyecto.integrantes)} miembros"),
                ),
                html.span(
                    {"className": "flex items-center space-x-1"},
                    html.span("📌"),
                    html.span(f"{len(tareasActivas)} activas"),
                ),
            ),
        ),
        html.div(
            {"className": "pt-4 border-t border-slate-100 mt-4 space-y-1.5"},
            html.div(
                {"className": "w-full bg-slate-100 h-2 rounded-full overflow-hidden"},
                html.div(
                    {
                        "className": f"{colorBarra} h-full rounded-full transition-all duration-300",
                        "style": {"width": f"{avance}%"},
                    }
                ),
            ),
            html.div(
                {
                    "className": "flex justify-between items-center text-[11px] text-slate-400"
                },
                html.span("Avance de entregables"),
                html.span(
                    {"className": "font-medium text-slate-600"},
                    f"{avance:.1f}%",
                ),
            ),
        ),
    )


def renderizarEstadoCatalogoVacio(
    alAbrirModalCreacion: Callable[[], None],
) -> VdomDict:
    """Renderiza la vista de bienvenida minimalista orientadora cuando no existen proyectos."""
    return html.div(
        {
            "id": "estado-catalogo-vacio",
            "className": "flex-1 flex flex-col items-center justify-center p-8 text-center my-auto",
        },
        html.div(
            {
                "className": (
                    "max-w-lg w-full bg-white p-10 rounded-2xl shadow-sm border "
                    "border-slate-200/90 space-y-5 animate-in fade-in duration-200"
                )
            },
            html.div(
                {
                    "className": (
                        "w-16 h-16 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center "
                        "justify-center mx-auto text-3xl font-bold shadow-inner"
                    )
                },
                "✨",
            ),
            html.div(
                {"className": "space-y-2"},
                html.h2(
                    {"className": f"{TITULO_SECCION} text-xl"},
                    "Bienvenido a AgilBan",
                ),
                html.p(
                    {"className": "text-sm text-slate-500 leading-relaxed"},
                    "Aun no tienes proyectos registrados en el sistema. Inicia tu planificacion "
                    "creando tu primer proyecto con su estructura de desglose (EDT) y tableros Kanban.",
                ),
            ),
            html.div(
                {"className": "pt-3"},
                html.button(
                    {
                        "id": "btn-crear-primer-proyecto",
                        "onClick": lambda e: alAbrirModalCreacion(),
                        "className": f"{BOTON_PRIMARIO} px-6 py-2.5 text-base shadow",
                    },
                    "+ Crear Primer Proyecto",
                ),
            ),
        ),
    )


def renderizarEstadoBusquedaSinResultados(
    textoBusqueda: str,
    alBuscar: Callable[[str], None],
) -> VdomDict:
    """Renderiza el estado especifico de busqueda sin coincidencias con accion para limpiar."""
    return html.div(
        {
            "id": "estado-busqueda-sin-resultados",
            "className": "flex-1 flex flex-col items-center justify-center p-12 text-center",
        },
        html.div(
            {
                "className": (
                    "max-w-md w-full bg-white p-8 rounded-2xl shadow-sm border "
                    "border-slate-200 space-y-4 animate-in fade-in duration-150"
                )
            },
            html.div(
                {
                    "className": (
                        "w-12 h-12 bg-amber-50 text-amber-600 rounded-xl flex items-center "
                        "justify-center mx-auto text-2xl"
                    )
                },
                "🔍",
            ),
            html.h3(
                {"className": "text-base font-semibold text-slate-800"},
                "Sin coincidencias de busqueda",
            ),
            html.p(
                {"className": "text-sm text-slate-500 leading-relaxed"},
                f"No se encontraron proyectos que coincidan con '{textoBusqueda}'. "
                "Intenta con otro termino o limpia el filtro para ver todo el catalogo.",
            ),
            html.button(
                {
                    "id": "btn-limpiar-busqueda",
                    "onClick": lambda e: alBuscar(""),
                    "className": f"{BOTON_SECUNDARIO} mt-2",
                },
                "Limpiar Busqueda",
            ),
        ),
    )


def renderizarVistaInicio(
    proyectos: tuple[Proyecto, ...],
    textoBusqueda: str,
    alBuscar: Callable[[str], None],
    alSeleccionarProyecto: Callable[[str], None],
    alAbrirModalCreacion: Callable[[], None],
    alEliminarProyecto: Callable[[str], None] | None = None,
) -> VdomDict:
    """Funcion pura de renderizado para la vista de inicio y catalogo de proyectos."""
    # 1. Caso de catalogo vacio absoluto
    if len(proyectos) == 0:
        return html.div(
            {
                "id": "vista-inicio-raiz",
                "className": "flex-1 flex flex-col p-6 max-w-7xl w-full mx-auto",
            },
            renderizarEstadoCatalogoVacio(alAbrirModalCreacion),
        )

    # 2. Caso con proyectos en catalogo: aplicar filtro local
    proyectosFiltrados = filtrarProyectosPorNombre(proyectos, textoBusqueda)

    return html.div(
        {
            "id": "vista-inicio-raiz",
            "className": "flex-1 flex flex-col p-6 max-w-7xl w-full mx-auto space-y-6",
        },
        # Barra de Cabecera y Controles de Filtro
        html.div(
            {
                "className": (
                    "flex flex-col md:flex-row md:items-center justify-between pb-4 "
                    f"{BORDE_SUAVE} border-b gap-4"
                )
            },
            html.div(
                {"className": "space-y-0.5"},
                html.h1({"className": TITULO_PANTALLA}, "Mis Proyectos"),
                html.p(
                    {"className": SUBTITULO_PANTALLA},
                    f"{len(proyectos)} iniciativas en curso bajo gestion agil local.",
                ),
            ),
            html.div(
                {"className": "flex items-center space-x-3"},
                # Campo de busqueda local
                html.div(
                    {"className": "relative w-64 md:w-80"},
                    html.input(
                        {
                            "id": "input-busqueda-proyectos",
                            "type": "text",
                            "placeholder": "Buscar por nombre de proyecto…",
                            "value": textoBusqueda,
                            "onChange": lambda e: alBuscar(e["target"]["value"]),
                            "className": f"{INPUT_TEXTO} pr-8",
                        }
                    ),
                    (
                        html.button(
                            {
                                "id": "btn-icono-limpiar-busqueda",
                                "onClick": lambda e: alBuscar(""),
                                "className": "absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600 text-xs font-bold",
                            },
                            "✕",
                        )
                        if textoBusqueda
                        else html.span(
                            {
                                "className": "absolute right-3 top-2.5 text-slate-400 text-sm pointer-events-none"
                            },
                            "🔍",
                        )
                    ),
                ),
                # Boton de nuevo proyecto
                html.button(
                    {
                        "id": "btn-abrir-modal-creacion",
                        "onClick": lambda e: alAbrirModalCreacion(),
                        "className": BOTON_PRIMARIO,
                    },
                    "+ Nuevo Proyecto",
                ),
            ),
        ),
        # Cuerpo condicional: Cuadricula vs Cero Coincidencias
        (
            renderizarEstadoBusquedaSinResultados(textoBusqueda, alBuscar)
            if len(proyectosFiltrados) == 0
            else html.div(
                {
                    "id": "cuadricula-proyectos",
                    "className": "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in fade-in duration-150",
                },
                *[
                    renderizarTarjetaProyecto(
                        p, alSeleccionarProyecto, alEliminarProyecto
                    )
                    for p in proyectosFiltrados
                ],
            )
        ),
    )


@component
def vistaInicio(
    proyectos: tuple[Proyecto, ...],
    textoBusqueda: str,
    alBuscar: Callable[[str], None],
    alSeleccionarProyecto: Callable[[str], None],
    alAbrirModalCreacion: Callable[[], None],
    alEliminarProyecto: Callable[[str], None] | None = None,
) -> Any:
    """Componente ReactPy para la pantalla de inicio y catalogo de proyectos."""
    return renderizarVistaInicio(
        proyectos=proyectos,
        textoBusqueda=textoBusqueda,
        alBuscar=alBuscar,
        alSeleccionarProyecto=alSeleccionarProyecto,
        alAbrirModalCreacion=alAbrirModalCreacion,
        alEliminarProyecto=alEliminarProyecto,
    )
