"""Componente raiz y enrutador SPA para la aplicacion web AgilBan en ReactPy.

Gestiona el estado global reactivo de la Single Page Application (SPA):
navegacion entre vistas (Inicio, Workspace, Metricas) sin recarga del navegador,
proyecto y paquete activos, tarea en edicion, retroceso pendiente,
modal de creacion de proyectos, borrador, estado explicito de guardado,
clave idempotente de creacion y confirmacion de cierre de panel.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from reactpy import component, html, use_state

from app.adapters.repositorioSqlite import (
    actualizarNombrePaquete,
    eliminarIntegrante,
    eliminarPaqueteVacio,
    guardarProyectoCompleto,
    recuperarProyectos,
)
from app.core.edt import (
    calcularEstadoPaquete,
    obtenerTareasActivas,
)
from app.domain.catalogos import EstadoKanban
from app.domain.modelos import Integrante, PaqueteTrabajo, Proyecto, Tarea
from app.domain.monadas import Alguno, Ninguno, Opcion
from app.ui.web.barraLateral import barraLateralEdt
from app.ui.web.estilos import (
    BORDE_SUAVE,
    BOTON_PRIMARIO,
    FONDO_LIENZO,
    FONDO_SUPERFICIE,
    INDICADOR_GUARDADO,
    obtenerClaseEstadoPaquete,
)
from app.ui.web.inicio import vistaInicio
from app.ui.web.modalProyecto import modalCreacionProyecto


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
    versionDatos, setVersionDatos = use_state(0)

    def forzarActualizacion() -> None:
        setVersionDatos(lambda v: v + 1)

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
            proyectosActuales: tuple[Proyecto, ...] = ()
            if conexion is not None:
                resRecuperacion = recuperarProyectos(conexion)
                if resRecuperacion.esExito():
                    proyectosActuales = resRecuperacion.obtenerValor()

            proyectoActivo: Proyecto | None = None
            if idProyectoActivo.esAlguno():
                proyectoActivo = next(
                    (
                        p
                        for p in proyectosActuales
                        if p.idProyecto == idProyectoActivo.obtenerValor()
                    ),
                    None,
                )
            if proyectoActivo is None and len(proyectosActuales) > 0:
                proyectoActivo = proyectosActuales[0]

            if proyectoActivo is None:
                return html.main(
                    {
                        "id": "vista-workspace-contenedor",
                        "className": (
                            "flex-1 flex flex-col overflow-hidden animate-in fade-in duration-150"
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
                                        "w-12 h-12 bg-amber-50 text-amber-600 rounded-xl flex items-center "
                                        "justify-center mx-auto text-xl font-bold"
                                    )
                                },
                                "📁",
                            ),
                            html.h2(
                                {"className": "text-lg font-semibold text-slate-800"},
                                "No hay proyecto seleccionado",
                            ),
                            html.p(
                                {"className": "text-sm text-slate-500 leading-relaxed"},
                                "Selecciona un proyecto desde la pantalla de inicio o crea uno nuevo.",
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

            idPaqueteActual = ""
            if idPaqueteSeleccionado.esAlguno() and any(
                p.idPaquete == idPaqueteSeleccionado.obtenerValor()
                for p in proyectoActivo.paquetes
            ):
                idPaqueteActual = idPaqueteSeleccionado.obtenerValor()
            elif len(proyectoActivo.paquetes) > 0:
                idPaqueteActual = proyectoActivo.paquetes[0].idPaquete

            paqueteActivo = next(
                (p for p in proyectoActivo.paquetes if p.idPaquete == idPaqueteActual),
                None,
            )

            def agregarPaqueteWorkspace(nuevoPaquete: PaqueteTrabajo) -> None:
                if conexion is not None and proyectoActivo is not None:
                    nuevoProyecto = replace(
                        proyectoActivo,
                        paquetes=proyectoActivo.paquetes + (nuevoPaquete,),
                    )
                    guardarProyectoCompleto(conexion, nuevoProyecto)
                setIdPaqueteSeleccionado(Alguno(nuevoPaquete.idPaquete))
                forzarActualizacion()

            def renombrarPaqueteWorkspace(idPaquete: str, nuevoNombre: str) -> None:
                if conexion is not None:
                    actualizarNombrePaquete(conexion, idPaquete, nuevoNombre)
                forzarActualizacion()

            def eliminarPaqueteWorkspace(idPaquete: str) -> None:
                if conexion is not None:
                    eliminarPaqueteVacio(conexion, idPaquete)
                if (
                    idPaqueteSeleccionado.esAlguno()
                    and idPaqueteSeleccionado.obtenerValor() == idPaquete
                ):
                    restantes = tuple(
                        p.idPaquete
                        for p in proyectoActivo.paquetes
                        if p.idPaquete != idPaquete
                    )
                    if restantes:
                        setIdPaqueteSeleccionado(Alguno(restantes[0]))
                    else:
                        setIdPaqueteSeleccionado(_castOpcion(Ninguno(), str))
                forzarActualizacion()

            def agregarIntegranteWorkspace(nuevoIntegrante: Integrante) -> None:
                if conexion is not None and proyectoActivo is not None:
                    nuevoProyecto = replace(
                        proyectoActivo,
                        integrantes=proyectoActivo.integrantes + (nuevoIntegrante,),
                    )
                    guardarProyectoCompleto(conexion, nuevoProyecto)
                forzarActualizacion()

            def eliminarIntegranteWorkspace(cedula: str) -> None:
                if conexion is not None and proyectoActivo is not None:
                    eliminarIntegrante(conexion, cedula, proyectoActivo.idProyecto)
                forzarActualizacion()

            def renderizarAreaCentralWorkspace(
                proyecto: Proyecto, paquete: PaqueteTrabajo | None
            ) -> Any:
                if paquete is None:
                    return html.div(
                        {
                            "id": "workspace-sin-paquetes-area",
                            "className": "flex-1 flex items-center justify-center p-8 text-center",
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
                                        "w-12 h-12 bg-amber-50 text-amber-600 rounded-xl flex items-center "
                                        "justify-center mx-auto text-xl font-bold"
                                    )
                                },
                                "📦",
                            ),
                            html.h2(
                                {"className": "text-lg font-semibold text-slate-800"},
                                "Proyecto sin Paquetes EDT",
                            ),
                            html.p(
                                {"className": "text-sm text-slate-500 leading-relaxed"},
                                "Agrega tu primer paquete de trabajo desde la barra lateral para comenzar a gestionar tareas en el tablero Kanban.",
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
                    )

                estadoDerivado = calcularEstadoPaquete(paquete)
                claseBadge = obtenerClaseEstadoPaquete(estadoDerivado)
                tareasActivas = obtenerTareasActivas(paquete)

                return html.div(
                    {
                        "id": "workspace-contenido-paquete",
                        "className": "flex-1 flex flex-col h-full overflow-hidden",
                    },
                    html.header(
                        {
                            "id": "cabecera-paquete-activo",
                            "className": (
                                "bg-white border-b border-slate-200 px-6 py-4 flex items-center "
                                "justify-between shadow-sm z-10"
                            ),
                        },
                        html.div(
                            {"className": "space-y-1 min-w-0"},
                            html.div(
                                {
                                    "className": "flex items-center space-x-2 text-xs text-slate-400"
                                },
                                html.span(
                                    {
                                        "id": "breadcrumb-proyecto",
                                        "className": "font-medium text-slate-500 truncate",
                                    },
                                    proyecto.nombre,
                                ),
                                html.span("/"),
                                html.span(
                                    {"className": "font-semibold text-indigo-600"},
                                    paquete.idPaquete,
                                ),
                            ),
                            html.div(
                                {"className": "flex items-center space-x-3"},
                                html.h1(
                                    {
                                        "id": "titulo-paquete-activo",
                                        "className": "text-xl font-bold text-slate-900 truncate",
                                    },
                                    paquete.nombre,
                                ),
                                html.span(
                                    {
                                        "id": "badge-estado-paquete-activo",
                                        "className": claseBadge,
                                    },
                                    estadoDerivado.value,
                                ),
                                html.span(
                                    {
                                        "id": "conteo-tareas-paquete-activo",
                                        "className": (
                                            "text-xs text-slate-400 font-medium px-2 py-0.5 rounded bg-slate-100"
                                        ),
                                    },
                                    f"{len(tareasActivas)} tareas activas",
                                ),
                            ),
                        ),
                        html.div(
                            {"className": "flex items-center space-x-3"},
                            html.button(
                                {
                                    "id": "btn-nueva-tarea-kanban",
                                    "className": BOTON_PRIMARIO,
                                },
                                "+ Nueva Tarea",
                            ),
                        ),
                    ),
                    html.div(
                        {
                            "id": "tablero-kanban-area",
                            "className": "flex-1 overflow-x-auto p-6 flex gap-6 bg-slate-50",
                        },
                        html.div(
                            {
                                "className": (
                                    "flex-1 flex items-center justify-center p-8 text-center border-2 "
                                    "border-dashed border-slate-200 rounded-2xl m-4 bg-white/50"
                                )
                            },
                            html.div(
                                {"className": "max-w-md space-y-2"},
                                html.div(
                                    {
                                        "className": (
                                            "w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center "
                                            "justify-center mx-auto text-lg font-bold"
                                        )
                                    },
                                    "📌",
                                ),
                                html.h3(
                                    {
                                        "className": "text-sm font-bold text-slate-800 uppercase tracking-wider"
                                    },
                                    f"Tablero Kanban — {paquete.nombre}",
                                ),
                                html.p(
                                    {
                                        "className": "text-xs text-slate-500 leading-relaxed"
                                    },
                                    (
                                        f"Visualización de las 4 columnas delimitadas con {len(tareasActivas)} "
                                        "tareas activas para este paquete."
                                    ),
                                ),
                            ),
                        ),
                    ),
                )

            return html.main(
                {
                    "id": "vista-workspace-contenedor",
                    "className": (
                        "flex-1 flex flex-row overflow-hidden animate-in fade-in duration-150"
                    ),
                },
                barraLateralEdt(
                    proyecto=proyectoActivo,
                    idPaqueteSeleccionado=idPaqueteActual,
                    alSeleccionarPaquete=seleccionarPaquete,
                    alAgregarPaquete=agregarPaqueteWorkspace,
                    alRenombrarPaquete=renombrarPaqueteWorkspace,
                    alEliminarPaquete=eliminarPaqueteWorkspace,
                    alVolverInicio=navegarAInicio,
                    alAbrirMetricas=navegarAMetricas,
                    alAgregarIntegrante=agregarIntegranteWorkspace,
                    alEliminarIntegrante=eliminarIntegranteWorkspace,
                ),
                html.div(
                    {
                        "id": "area-central-workspace",
                        "className": (
                            "flex-1 flex flex-col overflow-y-auto bg-slate-50 min-w-0"
                        ),
                    },
                    renderizarAreaCentralWorkspace(proyectoActivo, paqueteActivo),
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

    def guardarNuevoProyecto(nuevoProyecto: Proyecto) -> None:
        if conexion is not None:
            guardarProyectoCompleto(conexion, nuevoProyecto)
        setIdProyectoActivo(Alguno(nuevoProyecto.idProyecto))
        if len(nuevoProyecto.paquetes) > 0:
            setIdPaqueteSeleccionado(Alguno(nuevoProyecto.paquetes[0].idPaquete))
        setVistaActiva("WORKSPACE")
        setModalCreacionAbierto(False)
        forzarActualizacion()

    # -------------------------------------------------------------------------
    # 5. Renderizado de Modales y Superposiciones
    # -------------------------------------------------------------------------
    def renderizarSuperposiciones() -> Any:
        if not modalCreacionAbierto:
            return html.div()

        proyectosActuales: tuple[Proyecto, ...] = ()
        if conexion is not None:
            resRecuperacion = recuperarProyectos(conexion)
            if resRecuperacion.esExito():
                proyectosActuales = resRecuperacion.obtenerValor()

        return modalCreacionProyecto(
            alCerrar=cerrarModalNuevoProyecto,
            alGuardar=guardarNuevoProyecto,
            proyectosExistentes=proyectosActuales,
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
        "data-version-datos": str(versionDatos),
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
