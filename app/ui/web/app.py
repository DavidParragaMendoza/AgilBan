"""Componente raiz y enrutador SPA para la aplicacion web AgilBan en ReactPy.

Gestiona el estado global reactivo de la Single Page Application (SPA):
navegacion entre vistas (Inicio, Workspace, Metricas) sin recarga del navegador,
proyecto y paquete activos, tarea en edicion, retroceso pendiente,
modal de creacion de proyectos, borrador, estado explicito de guardado,
clave idempotente de creacion y confirmacion de cierre de panel.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum
from typing import Any

from reactpy import component, html, use_state

from app.adapters.repositorioSqlite import recuperarProyectos
from app.domain.catalogos import EstadoKanban
from app.domain.modelos import Proyecto, Tarea
from app.domain.monadas import Alguno, Ninguno, Opcion
from app.ui.web.estilos import (
    BORDE_SUAVE,
    BOTON_PRIMARIO,
    FONDO_LIENZO,
    FONDO_SUPERFICIE,
    INDICADOR_GUARDADO,
)
from app.ui.web.inicio import vistaInicio


class EstadoGuardado(Enum):
    """Estado explicito del proceso de autoguardado en el panel lateral."""

    GUARDANDO = "Guardando…"
    GUARDADO = "✓ Guardado"
    ERROR = "No se pudo guardar"


@dataclass(frozen=True)
class SolicitudCreacionTarea:
    """Datos inmutables para el alta de tareas con clave idempotente."""

    idPaquete: str
    titulo: str
    claveSolicitud: str


def _castOpcion(opcion: Opcion[Any], _tipo: type) -> Opcion[Any]:
    """Helper tipado inmutable para inicializacion de opciones en use_state."""
    return opcion


@component
def componenteApp(conexion: sqlite3.Connection | None = None) -> Any:
    """Componente raiz y enrutador reactivo montado en el servidor web.

    Administra la totalidad del arbol de estado inmutable de la SPA.
    """
    # -------------------------------------------------------------------------
    # 1. Variables de Estado Global Reactivo (use_state)
    # -------------------------------------------------------------------------
    vistaActiva, setVistaActiva = use_state("INICIO")
    idProyectoActivo, setIdProyectoActivo = use_state(_castOpcion(Ninguno(), str))
    idPaqueteSeleccionado, setIdPaqueteSeleccionado = use_state(
        _castOpcion(Ninguno(), str)
    )
    tareaEnEdicion, setTareaEnEdicion = use_state(_castOpcion(Ninguno(), Tarea))
    retrocesoPendiente, setRetrocesoPendiente = use_state(
        _castOpcion(Ninguno(), tuple[Tarea, EstadoKanban])
    )
    modalCreacionAbierto, setModalCreacionAbierto = use_state(False)
    textoBusquedaProyectos, setTextoBusquedaProyectos = use_state("")
    estadoGuardado, setEstadoGuardado = use_state(EstadoGuardado.GUARDADO)
    borradorTarea, setBorradorTarea = use_state(_castOpcion(Ninguno(), Tarea))
    solicitudCreacionTarea, setSolicitudCreacionTarea = use_state(
        _castOpcion(Ninguno(), SolicitudCreacionTarea)
    )
    cierrePendiente, setCierrePendiente = use_state(False)

    # -------------------------------------------------------------------------
    # 2. Acciones y Callbacks Puros de Navegacion SPA
    # -------------------------------------------------------------------------
    def navegarAInicio(evento: Any = None) -> None:
        setVistaActiva("INICIO")

    def navegarAWorkspace(evento: Any = None) -> None:
        setVistaActiva("WORKSPACE")

    def navegarAMetricas(evento: Any = None) -> None:
        setVistaActiva("METRICAS")

    def abrirModalNuevoProyecto(evento: Any = None) -> None:
        setModalCreacionAbierto(True)

    def cerrarModalNuevoProyecto(evento: Any = None) -> None:
        setModalCreacionAbierto(False)

    def seleccionarProyecto(idProyecto: str) -> None:
        setIdProyectoActivo(Alguno(idProyecto))
        setVistaActiva("WORKSPACE")

    def seleccionarPaquete(idPaquete: str) -> None:
        setIdPaqueteSeleccionado(Alguno(idPaquete))

    def editarTarea(tarea: Tarea) -> None:
        setTareaEnEdicion(Alguno(tarea))
        setBorradorTarea(Alguno(tarea))
        setEstadoGuardado(EstadoGuardado.GUARDADO)

    def programarRetroceso(tarea: Tarea, destino: EstadoKanban) -> None:
        setRetrocesoPendiente(Alguno((tarea, destino)))

    def registrarSolicitudTarea(idPaquete: str, titulo: str, clave: str) -> None:
        setSolicitudCreacionTarea(
            Alguno(SolicitudCreacionTarea(idPaquete, titulo, clave))
        )

    def marcarCierrePendiente(pendiente: bool) -> None:
        setCierrePendiente(pendiente)

    # -------------------------------------------------------------------------
    # 3. Renderizado de la Barra Superior de Navegacion
    # -------------------------------------------------------------------------
    def renderizarNavegacion() -> Any:
        pestanaInicioClase = (
            "px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors "
            + (
                "bg-indigo-50 text-indigo-700"
                if vistaActiva == "INICIO"
                else "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            )
        )
        pestanaWorkspaceClase = (
            "px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors "
            + (
                "bg-indigo-50 text-indigo-700"
                if vistaActiva == "WORKSPACE"
                else "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            )
        )
        pestanaMetricasClase = (
            "px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors "
            + (
                "bg-indigo-50 text-indigo-700"
                if vistaActiva == "METRICAS"
                else "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            )
        )

        return html.header(
            {
                "id": "agilban-encabezado-navegacion",
                "className": (
                    f"{FONDO_SUPERFICIE} {BORDE_SUAVE} border-b px-6 py-3.5 "
                    "flex items-center justify-between shadow-sm sticky top-0 z-30"
                ),
            },
            html.div(
                {"className": "flex items-center space-x-6"},
                # Isotipo y Marca
                html.button(
                    {
                        "id": "btn-logo-agilban",
                        "onClick": navegarAInicio,
                        "className": (
                            "flex items-center space-x-3 text-left focus:outline-none group"
                        ),
                    },
                    html.div(
                        {
                            "className": (
                                "w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center "
                                "text-white font-bold text-sm shadow group-hover:bg-indigo-700 transition-colors"
                            )
                        },
                        "AB",
                    ),
                    html.div(
                        {"className": "flex flex-col"},
                        html.span(
                            {
                                "className": "text-lg font-bold tracking-tight text-slate-800 leading-none"
                            },
                            "AgilBan",
                        ),
                        html.span(
                            {
                                "className": "text-[10px] font-medium text-slate-400 mt-0.5 tracking-wider uppercase"
                            },
                            "Gestion Agil",
                        ),
                    ),
                ),
                # Enlaces de Navegacion SPA
                html.nav(
                    {
                        "id": "agilban-menu-spa",
                        "className": "flex items-center space-x-1 border-l border-slate-200 pl-6",
                    },
                    html.button(
                        {
                            "id": "nav-item-inicio",
                            "onClick": navegarAInicio,
                            "className": pestanaInicioClase,
                        },
                        "Inicio",
                    ),
                    html.button(
                        {
                            "id": "nav-item-workspace",
                            "onClick": navegarAWorkspace,
                            "className": pestanaWorkspaceClase,
                        },
                        "Workspace",
                    ),
                    html.button(
                        {
                            "id": "nav-item-metricas",
                            "onClick": navegarAMetricas,
                            "className": pestanaMetricasClase,
                        },
                        "Métricas",
                    ),
                ),
            ),
            # Acciones del Encabezado
            html.div(
                {"className": "flex items-center space-x-3"},
                html.span(
                    {"className": INDICADOR_GUARDADO},
                    estadoGuardado.value,
                ),
                html.button(
                    {
                        "id": "btn-abrir-modal-nuevo-proyecto",
                        "onClick": abrirModalNuevoProyecto,
                        "className": BOTON_PRIMARIO,
                    },
                    "+ Nuevo Proyecto",
                ),
            ),
        )

    # -------------------------------------------------------------------------
    # 4. Renderizado Condicional de Contenido Principal Segun vistaActiva
    # -------------------------------------------------------------------------
    def renderizarCuerpoPrincipal() -> Any:
        if vistaActiva == "INICIO":
            proyectosActuales: tuple[Proyecto, ...] = ()
            if conexion is not None:
                resRecuperacion = recuperarProyectos(conexion)
                if resRecuperacion.esExito():
                    proyectosActuales = resRecuperacion.obtenerValor()

            return html.main(
                {
                    "id": "vista-inicio-contenedor",
                    "className": (
                        "flex-1 flex flex-col overflow-y-auto animate-in fade-in duration-150"
                    ),
                },
                vistaInicio(
                    proyectos=proyectosActuales,
                    textoBusqueda=textoBusquedaProyectos,
                    alBuscar=setTextoBusquedaProyectos,
                    alSeleccionarProyecto=seleccionarProyecto,
                    alAbrirModalCreacion=abrirModalNuevoProyecto,
                ),
            )

        if vistaActiva == "WORKSPACE":
            return html.main(
                {
                    "id": "vista-workspace-contenedor",
                    "className": "flex-1 flex flex-col overflow-hidden animate-in fade-in duration-150",
                },
                html.div(
                    {
                        "className": "flex-1 flex items-center justify-center p-8 text-center"
                    },
                    html.div(
                        {
                            "className": (
                                "max-w-md w-full bg-white p-8 rounded-2xl shadow-sm border "
                                "border-slate-200 space-y-4"
                            )
                        },
                        html.div(
                            {
                                "className": (
                                    "w-12 h-12 bg-emerald-50 text-emerald-600 rounded-xl flex items-center "
                                    "justify-center mx-auto text-xl font-bold"
                                )
                            },
                            "📋",
                        ),
                        html.h2(
                            {"className": "text-lg font-semibold text-slate-800"},
                            "Espacio de Trabajo (Workspace)",
                        ),
                        html.p(
                            {"className": "text-sm text-slate-500 leading-relaxed"},
                            "Tablero Kanban de 4 columnas delimitadas y desglose de paquetes EDT.",
                        ),
                        html.button(
                            {
                                "id": "btn-volver-a-inicio-desde-ws",
                                "onClick": navegarAInicio,
                                "className": "text-sm text-indigo-600 font-medium hover:underline",
                            },
                            "← Volver a Mis Proyectos",
                        ),
                    ),
                ),
            )

        # Caso vistaActiva == "METRICAS"
        return html.main(
            {
                "id": "vista-metricas-contenedor",
                "className": (
                    "flex-1 flex flex-col overflow-hidden p-6 max-w-7xl w-full mx-auto "
                    "animate-in fade-in duration-150"
                ),
            },
            html.div(
                {
                    "className": "flex-1 flex items-center justify-center p-8 text-center"
                },
                html.div(
                    {
                        "className": (
                            "max-w-md w-full bg-white p-8 rounded-2xl shadow-sm border "
                            "border-slate-200 space-y-4"
                        )
                    },
                    html.div(
                        {
                            "className": (
                                "w-12 h-12 bg-purple-50 text-purple-600 rounded-xl flex items-center "
                                "justify-center mx-auto text-xl font-bold"
                            )
                        },
                        "📊",
                    ),
                    html.h2(
                        {"className": "text-lg font-semibold text-slate-800"},
                        "Panel de Metricas y Analitica",
                    ),
                    html.p(
                        {"className": "text-sm text-slate-500 leading-relaxed"},
                        "Indicadores de avance, distribucion de tareas y auditoria de cuellos de botella.",
                    ),
                    html.button(
                        {
                            "id": "btn-volver-a-inicio-desde-metricas",
                            "onClick": navegarAInicio,
                            "className": "text-sm text-indigo-600 font-medium hover:underline",
                        },
                        "← Volver a Mis Proyectos",
                    ),
                ),
            ),
        )

    # -------------------------------------------------------------------------
    # 5. Renderizado de Modales y Superposiciones
    # -------------------------------------------------------------------------
    def renderizarSuperposiciones() -> Any:
        if not modalCreacionAbierto:
            return html.div()

        return html.div(
            {
                "id": "modal-creacion-proyecto-overlay",
                "className": (
                    "fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center "
                    "justify-center z-50 p-4"
                ),
            },
            html.div(
                {
                    "className": (
                        "bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-md w-full "
                        "p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150"
                    )
                },
                html.div(
                    {"className": "flex items-center justify-between"},
                    html.h3(
                        {"className": "text-lg font-bold text-slate-900"},
                        "Crear Nuevo Proyecto",
                    ),
                    html.button(
                        {
                            "id": "btn-cerrar-modal-x",
                            "onClick": cerrarModalNuevoProyecto,
                            "className": "text-slate-400 hover:text-slate-600 text-lg font-bold",
                        },
                        "✕",
                    ),
                ),
                html.p(
                    {"className": "text-sm text-slate-500"},
                    "Formulario guiado con generacion automatica de paquetes e integrantes reactivos.",
                ),
                html.div(
                    {"className": "flex justify-end space-x-3 pt-4"},
                    html.button(
                        {
                            "id": "btn-cancelar-modal-proyecto",
                            "onClick": cerrarModalNuevoProyecto,
                            "className": (
                                "px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 "
                                "hover:bg-slate-200 rounded-lg transition-colors"
                            ),
                        },
                        "Cancelar",
                    ),
                ),
            ),
        )

    # Variables y callbacks accesibles para inspeccion y reactividad
    datosEstado = {
        "data-vista": vistaActiva,
        "data-proyecto": (
            idProyectoActivo.obtenerValor() if idProyectoActivo.esAlguno() else ""
        ),
        "data-paquete": (
            idPaqueteSeleccionado.obtenerValor()
            if idPaqueteSeleccionado.esAlguno()
            else ""
        ),
        "data-tarea": (
            tareaEnEdicion.obtenerValor().idTarea if tareaEnEdicion.esAlguno() else ""
        ),
        "data-retroceso": str(retrocesoPendiente.esAlguno()),
        "data-guardado": estadoGuardado.value,
        "data-borrador": str(borradorTarea.esAlguno()),
        "data-solicitud": str(solicitudCreacionTarea.esAlguno()),
        "data-cierre-pendiente": str(cierrePendiente),
        "data-has-conexion": str(conexion is not None),
    }

    # Registro de referencia para callbacks de ciclo de vida completo
    _manejadoresAcciones = (
        seleccionarProyecto,
        seleccionarPaquete,
        editarTarea,
        programarRetroceso,
        registrarSolicitudTarea,
        marcarCierrePendiente,
    )
    if len(_manejadoresAcciones) == 0:
        pass

    # -------------------------------------------------------------------------
    # 6. Retorno Estructural del Componente Raiz
    # -------------------------------------------------------------------------
    return html.div(
        {
            "id": "agilban-contenedor-raiz",
            "className": f"{FONDO_LIENZO} flex flex-col min-h-screen",
            **datosEstado,
        },
        renderizarNavegacion(),
        renderizarCuerpoPrincipal(),
        renderizarSuperposiciones(),
    )
