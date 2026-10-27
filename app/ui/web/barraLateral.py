# ruff: noqa: N999
"""Barra lateral dinamica de la EDT (Sidebar estilo Notion) y gestion de equipo.

Implementa RF-03 y RF-04 (EARS-03.1 a EARS-03.9):
- Enlace interactivo '← Mis Proyectos' para volver al Inicio (vistaActiva = 'INICIO').
- Encabezado con titulo del proyecto activo, tipo de proyecto y barra de avance global.
- Boton directo para alternar a la pantalla de 'Metricas' (vistaActiva = 'METRICAS').
- Lista de paquetes de trabajo con insignia de estado derivado (calcularEstadoPaquete):
  'Sin Tareas', 'Pendiente', 'En progreso' y 'Terminado'.
- Seleccion reactiva de paquete actualizando idPaqueteSeleccionado en el estado global.
- Estado vacio orientador navegable con accion '+ Agregar Paquete' (EARS-03.9).
- Acciones de gestion de paquetes:
  * Agregar paquete con validacion de nombre (max. 80 caracteres, unico).
  * Renombrar paquete preservando tareas e historial intactos.
  * Eliminar paquete bloqueado si tiene tareas registradas (EARS-03.7).
- Acciones de gestion de equipo:
  * Visualizar integrantes y agregar nuevos (cedula de 10 digitos, nombre, cargo).
  * Eliminar integrante bloqueado si tiene tareas activas asignadas o es el unico (EARS-03.8).
"""

from __future__ import annotations

import re
from collections.abc import Callable

from reactpy import component, html, use_state
from reactpy.types import VdomDict

from app.core.edt import (
    calcularAvancePaquete,
    calcularEstadoPaquete,
    obtenerTareasActivas,
)
from app.core.metricas import calcularAvanceGlobal
from app.core.validador import (
    validarCedula,
    validarEliminacionIntegrante,
    validarEliminacionPaquete,
    validarNombreIntegrante,
    validarNombrePaquete,
)
from app.domain.catalogos import (
    CargoIntegrante,
    EstadoPaquete,
)
from app.domain.modelos import Integrante, PaqueteTrabajo, Proyecto, Tarea
from app.ui.web.estilos import (
    INPUT_ERROR,
    INPUT_TEXTO,
    TEXTO_ERROR_FORMULARIO,
    obtenerClaseEstadoPaquete,
)

_PATRON_ID_PAQUETE = re.compile(r"^PAQ-(\d+)$")


def generarIdPaqueteSecuencial(paquetesExistentes: tuple[PaqueteTrabajo, ...]) -> str:
    """Genera un identificador correlativo secuencial PAQ-NNN basado en los paquetes existentes."""
    mayor = 0
    for p in paquetesExistentes:
        coincidencia = _PATRON_ID_PAQUETE.match(p.idPaquete)
        if coincidencia:
            mayor = max(mayor, int(coincidencia.group(1)))
    return f"PAQ-{mayor + 1:03d}"


# ==============================================================================
# RENDERIZADORES PUROS Y DETERMINISTAS (VDOM)
# ==============================================================================


def renderizarAlertaContextual(
    mensaje: str,
    alCerrar: Callable[[], None],
) -> VdomDict:
    """Renderiza un banner de advertencia contextual para acciones bloqueadas."""
    if not mensaje:
        return html.div({"id": "alerta-contextual-sidebar", "className": "hidden"})

    return html.div(
        {
            "id": "alerta-contextual-sidebar",
            "className": (
                "mx-4 mt-3 p-3 bg-amber-50 border border-amber-200 rounded-xl "
                "text-amber-900 text-xs flex items-start justify-between gap-2 "
                "animate-in fade-in duration-150 shadow-sm"
            ),
        },
        html.div(
            {"className": "flex items-start gap-2"},
            html.span(
                {"className": "text-amber-600 font-bold text-sm leading-none"}, "⚠️"
            ),
            html.p(
                {
                    "id": "texto-alerta-contextual",
                    "className": "font-medium leading-relaxed",
                },
                mensaje,
            ),
        ),
        html.button(
            {
                "id": "btn-cerrar-alerta-sidebar",
                "onClick": lambda e: alCerrar(),
                "className": "text-amber-500 hover:text-amber-800 font-bold text-sm leading-none px-1",
                "title": "Cerrar advertencia",
            },
            "✕",
        ),
    )


def renderizarEncabezadoProyecto(
    proyecto: Proyecto,
    alVolverInicio: Callable[[], None],
    alAbrirMetricas: Callable[[], None],
) -> VdomDict:
    """Renderiza la cabecera del panel lateral con navegacion, titulo, tipo y metricas."""
    todasLasTareas = tuple(t for paq in proyecto.paquetes for t in paq.tareas)
    avance = calcularAvanceGlobal(todasLasTareas)
    colorBarra = "bg-emerald-500" if avance >= 100.0 else "bg-indigo-600"

    return html.div(
        {
            "id": "encabezado-sidebar-proyecto",
            "className": "p-5 border-b border-slate-200 space-y-3.5 bg-white",
        },
        # Enlace Mis Proyectos
        html.div(
            {"className": "flex items-center justify-between"},
            html.button(
                {
                    "id": "btn-volver-mis-proyectos",
                    "onClick": lambda e: alVolverInicio(),
                    "className": (
                        "inline-flex items-center space-x-1.5 text-xs font-semibold text-slate-500 "
                        "hover:text-indigo-600 transition-colors py-0.5 focus:outline-none"
                    ),
                },
                html.span({"className": "font-bold text-sm leading-none"}, "←"),
                html.span("Mis Proyectos"),
            ),
            html.span(
                {
                    "id": "badge-tipo-proyecto-sidebar",
                    "className": (
                        "px-2 py-0.5 rounded-full text-[10px] font-semibold "
                        "bg-slate-100 text-slate-600 border border-slate-200 truncate max-w-[140px]"
                    ),
                },
                proyecto.tipo.value,
            ),
        ),
        # Titulo del Proyecto
        html.div(
            {"className": "space-y-1"},
            html.h2(
                {
                    "id": "titulo-proyecto-sidebar",
                    "className": "text-base font-bold text-slate-900 tracking-tight leading-snug line-clamp-2",
                    "title": proyecto.nombre,
                },
                proyecto.nombre,
            ),
        ),
        # Barra de Avance Global de Entregables
        html.div(
            {"className": "space-y-1.5 pt-1"},
            html.div(
                {"className": "flex justify-between items-center text-xs"},
                html.span(
                    {
                        "className": "text-[11px] font-semibold text-slate-500 uppercase tracking-wider"
                    },
                    "Avance Entregables",
                ),
                html.span(
                    {
                        "id": "texto-avance-global-sidebar",
                        "className": "font-bold text-slate-700",
                    },
                    f"{avance:.1f}%",
                ),
            ),
            html.div(
                {
                    "className": "w-full bg-slate-100 rounded-full h-1.5 overflow-hidden",
                },
                html.div(
                    {
                        "id": "barra-progreso-global-sidebar",
                        "className": f"{colorBarra} h-1.5 rounded-full transition-all duration-300",
                        "style": {"width": f"{min(avance, 100.0)}%"},
                    }
                ),
            ),
        ),
        # Boton Directo a Metricas
        html.button(
            {
                "id": "btn-sidebar-metricas",
                "onClick": lambda e: alAbrirMetricas(),
                "className": (
                    "w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-lg "
                    "text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 "
                    "border border-indigo-200 transition-colors shadow-sm focus:outline-none"
                ),
            },
            html.span({"className": "text-sm"}, "📊"),
            html.span("Ver Métricas del Proyecto"),
        ),
    )


def renderizarEstadoVacioEdt(
    alIniciarCreacionPaquete: Callable[[], None],
) -> VdomDict:
    """Renderiza el estado vacio orientador cuando el proyecto no tiene paquetes de trabajo (EARS-03.9)."""
    return html.div(
        {
            "id": "sidebar-edt-vacio",
            "className": (
                "p-6 text-center bg-white rounded-xl border border-dashed border-slate-300 "
                "m-4 space-y-3 shadow-sm"
            ),
        },
        html.div(
            {
                "className": (
                    "w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center "
                    "justify-center mx-auto text-xl font-bold"
                )
            },
            "📦",
        ),
        html.div(
            {"className": "space-y-1"},
            html.h4(
                {
                    "className": "text-xs font-bold text-slate-800 uppercase tracking-wider"
                },
                "Sin Paquetes EDT",
            ),
            html.p(
                {"className": "text-xs text-slate-500 leading-relaxed"},
                "Este proyecto no contiene paquetes de trabajo estructurados aún.",
            ),
        ),
        html.button(
            {
                "id": "btn-agregar-primer-paquete",
                "onClick": lambda e: alIniciarCreacionPaquete(),
                "className": (
                    "inline-flex items-center justify-center px-3 py-1.5 rounded-lg "
                    "bg-indigo-600 text-white font-medium text-xs hover:bg-indigo-700 transition-colors shadow-sm"
                ),
            },
            "+ Agregar Paquete",
        ),
    )


def renderizarFilaNuevoPaquete(
    nombre: str,
    error: str,
    alCambiarNombre: Callable[[str], None],
    alGuardar: Callable[[], None],
    alCancelar: Callable[[], None],
) -> VdomDict:
    """Renderiza el formulario interactivo en linea para crear un paquete de trabajo."""
    claseInput = INPUT_ERROR if error else INPUT_TEXTO

    return html.div(
        {
            "id": "formulario-nuevo-paquete",
            "className": (
                "p-3 rounded-xl bg-white border-2 border-indigo-400 shadow-sm space-y-2 "
                "animate-in fade-in duration-150 mx-4 mb-2"
            ),
        },
        html.div(
            {"className": "flex items-center justify-between"},
            html.span(
                {
                    "className": "text-[11px] font-bold text-indigo-700 uppercase tracking-wider"
                },
                "Nuevo Paquete EDT",
            ),
            html.button(
                {
                    "onClick": lambda e: alCancelar(),
                    "className": "text-slate-400 hover:text-slate-600 text-xs font-bold",
                },
                "✕",
            ),
        ),
        html.input(
            {
                "id": "input-nombre-nuevo-paquete",
                "type": "text",
                "placeholder": "Nombre del paquete (máx. 80)",
                "value": nombre,
                "onChange": lambda e: alCambiarNombre(e["target"]["value"]),
                "className": f"{claseInput} text-xs py-1.5",
                "maxLength": 80,
                "autoFocus": True,
            }
        ),
        html.span(
            {
                "id": "error-nombre-nuevo-paquete",
                "className": TEXTO_ERROR_FORMULARIO if error else "hidden",
            },
            error,
        ),
        html.div(
            {"className": "flex items-center justify-end space-x-2 pt-1"},
            html.button(
                {
                    "id": "btn-cancelar-nuevo-paquete",
                    "onClick": lambda e: alCancelar(),
                    "className": "px-2.5 py-1 text-xs text-slate-600 hover:text-slate-800 rounded",
                },
                "Cancelar",
            ),
            html.button(
                {
                    "id": "btn-guardar-nuevo-paquete",
                    "onClick": lambda e: alGuardar(),
                    "className": "px-3 py-1 bg-indigo-600 text-white rounded text-xs font-semibold hover:bg-indigo-700 shadow-sm",
                },
                "Guardar",
            ),
        ),
    )


def renderizarFilaRenombrarPaquete(
    idPaquete: str,
    nombre: str,
    error: str,
    alCambiarNombre: Callable[[str], None],
    alGuardar: Callable[[], None],
    alCancelar: Callable[[], None],
) -> VdomDict:
    """Renderiza el formulario en linea para renombrar un paquete preservando sus tareas."""
    claseInput = INPUT_ERROR if error else INPUT_TEXTO

    return html.div(
        {
            "id": f"formulario-renombrar-paquete-{idPaquete}",
            "className": (
                "p-3 rounded-xl bg-white border-2 border-indigo-400 shadow-sm space-y-2 "
                "animate-in fade-in duration-150 mx-4 mb-2"
            ),
        },
        html.div(
            {"className": "flex items-center justify-between"},
            html.span(
                {
                    "className": "text-[11px] font-bold text-indigo-700 uppercase tracking-wider"
                },
                "Renombrar Paquete",
            ),
            html.button(
                {
                    "onClick": lambda e: alCancelar(),
                    "className": "text-slate-400 hover:text-slate-600 text-xs font-bold",
                },
                "✕",
            ),
        ),
        html.input(
            {
                "id": f"input-renombrar-paquete-{idPaquete}",
                "type": "text",
                "placeholder": "Nuevo nombre (máx. 80)",
                "value": nombre,
                "onChange": lambda e: alCambiarNombre(e["target"]["value"]),
                "className": f"{claseInput} text-xs py-1.5",
                "maxLength": 80,
                "autoFocus": True,
            }
        ),
        html.span(
            {
                "id": f"error-renombrar-paquete-{idPaquete}",
                "className": TEXTO_ERROR_FORMULARIO if error else "hidden",
            },
            error,
        ),
        html.div(
            {"className": "flex items-center justify-end space-x-2 pt-1"},
            html.button(
                {
                    "id": f"btn-cancelar-renombrar-{idPaquete}",
                    "onClick": lambda e: alCancelar(),
                    "className": "px-2.5 py-1 text-xs text-slate-600 hover:text-slate-800 rounded",
                },
                "Cancelar",
            ),
            html.button(
                {
                    "id": f"btn-guardar-renombrar-{idPaquete}",
                    "onClick": lambda e: alGuardar(),
                    "className": "px-3 py-1 bg-indigo-600 text-white rounded text-xs font-semibold hover:bg-indigo-700 shadow-sm",
                },
                "Actualizar",
            ),
        ),
    )


def renderizarItemPaquete(
    paquete: PaqueteTrabajo,
    estaSeleccionado: bool,
    alSeleccionarPaquete: Callable[[str], None],
    alIniciarRenombrado: Callable[[PaqueteTrabajo], None],
    alSolicitarEliminar: Callable[[PaqueteTrabajo], None],
) -> VdomDict:
    """Renderiza la tarjeta individual de un paquete en la lista EDT con insignias puras."""
    estadoDerivado: EstadoPaquete = calcularEstadoPaquete(paquete)
    claseBadgeEstado = obtenerClaseEstadoPaquete(estadoDerivado)
    tareasActivas = obtenerTareasActivas(paquete)
    avance = calcularAvancePaquete(paquete)

    tieneTareas = len(paquete.tareas) > 0
    tituloEliminar = (
        "No se puede eliminar un paquete con tareas asociadas"
        if tieneTareas
        else "Eliminar paquete de trabajo sin tareas"
    )

    claseContenedor = (
        "p-3 rounded-xl border transition-all duration-150 cursor-pointer relative mx-4 mb-2 group "
        + (
            "bg-white border-indigo-400 shadow-md ring-1 ring-indigo-400/50"
            if estaSeleccionado
            else "bg-white/80 hover:bg-white border-slate-200 shadow-sm hover:border-slate-300"
        )
    )

    return html.article(
        {
            "id": f"item-paquete-{paquete.idPaquete}",
            "onClick": lambda e, pid=paquete.idPaquete: alSeleccionarPaquete(pid),
            "className": claseContenedor,
        },
        # Fila Superior: Badge Derivado y Avance
        html.div(
            {"className": "flex items-center justify-between gap-2 mb-1.5"},
            html.span(
                {
                    "id": f"badge-estado-paquete-{paquete.idPaquete}",
                    "className": f"{claseBadgeEstado} text-[10px] py-0.5",
                },
                estadoDerivado.value,
            ),
            html.span(
                {
                    "id": f"texto-avance-paquete-{paquete.idPaquete}",
                    "className": "text-[11px] font-bold text-slate-500",
                },
                f"{avance:.0f}%",
            ),
        ),
        # Titulo del Paquete
        html.div(
            {"className": "flex items-start justify-between gap-1"},
            html.h3(
                {
                    "id": f"nombre-paquete-{paquete.idPaquete}",
                    "className": (
                        "text-xs font-bold leading-tight line-clamp-2 "
                        + ("text-indigo-900" if estaSeleccionado else "text-slate-800")
                    ),
                    "title": paquete.nombre,
                },
                paquete.nombre,
            ),
        ),
        # Fila Inferior: Conteo de Tareas y Acciones
        html.div(
            {
                "className": "flex items-center justify-between pt-2 mt-1 border-t border-slate-100 text-[11px] text-slate-500",
            },
            html.span(
                {
                    "id": f"conteo-tareas-paquete-{paquete.idPaquete}",
                    "className": "font-medium text-slate-500 flex items-center space-x-1",
                },
                f"{len(tareasActivas)} tareas activas",
            ),
            html.div(
                {
                    "className": "flex items-center space-x-1.5",
                    "onClick": lambda e: None,  # Evita propagacion a seleccion
                },
                html.button(
                    {
                        "id": f"btn-renombrar-paquete-{paquete.idPaquete}",
                        "onClick": lambda e, p=paquete: alIniciarRenombrado(p),
                        "className": "text-indigo-600 hover:text-indigo-800 hover:underline font-semibold text-[11px] px-1 py-0.5 rounded",
                        "title": "Renombrar paquete",
                    },
                    "Renombrar",
                ),
                html.button(
                    {
                        "id": f"btn-eliminar-paquete-{paquete.idPaquete}",
                        "onClick": lambda e, p=paquete: alSolicitarEliminar(p),
                        "className": (
                            "p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors "
                            + ("opacity-40 cursor-not-allowed" if tieneTareas else "")
                        ),
                        "title": tituloEliminar,
                    },
                    "🗑️",
                ),
            ),
        ),
    )


def renderizarConfirmacionEliminarPaquete(
    paquete: PaqueteTrabajo,
    alConfirmar: Callable[[], None],
    alCancelar: Callable[[], None],
) -> VdomDict:
    """Renderiza el cuadro de confirmacion para eliminar un paquete de trabajo sin tareas."""
    return html.div(
        {
            "id": f"confirmacion-eliminar-paquete-{paquete.idPaquete}",
            "className": (
                "p-3 rounded-xl bg-rose-50 border border-rose-200 shadow-sm space-y-2 "
                "animate-in fade-in duration-150 mx-4 mb-2"
            ),
        },
        html.div(
            {"className": "flex items-start space-x-2"},
            html.span(
                {"className": "text-rose-600 font-bold text-xs leading-none mt-0.5"},
                "⚠️",
            ),
            html.div(
                {"className": "text-xs text-rose-900"},
                html.p(
                    {"className": "font-semibold leading-tight"},
                    f"¿Eliminar '{paquete.nombre}'?",
                ),
                html.p(
                    {"className": "text-[11px] text-rose-700 mt-1 leading-tight"},
                    "El paquete no contiene tareas asociadas. Esta acción lo eliminará.",
                ),
            ),
        ),
        html.div(
            {"className": "flex items-center justify-end space-x-2 pt-1"},
            html.button(
                {
                    "id": f"btn-cancelar-eliminar-paquete-{paquete.idPaquete}",
                    "onClick": lambda e: alCancelar(),
                    "className": (
                        "px-2.5 py-1 text-xs text-slate-600 hover:text-slate-800 "
                        "bg-white border border-slate-200 rounded font-medium transition-colors"
                    ),
                },
                "Cancelar",
            ),
            html.button(
                {
                    "id": f"btn-confirmar-eliminar-paquete-{paquete.idPaquete}",
                    "onClick": lambda e: alConfirmar(),
                    "className": (
                        "px-3 py-1 bg-rose-600 text-white rounded text-xs font-semibold "
                        "hover:bg-rose-700 shadow-sm transition-colors"
                    ),
                },
                "Confirmar",
            ),
        ),
    )


def renderizarItemIntegrante(
    integrante: Integrante,
    esUltimo: bool,
    tieneTareasAsignadas: bool,
    alEliminar: Callable[[str], None],
    estaEnConfirmacion: bool = False,
) -> VdomDict:
    """Renderiza la fila de un miembro del equipo en la barra lateral."""
    iniciales = "".join(
        parte[0].upper() for parte in integrante.nombre.split() if parte
    )[:2]

    tituloBoton = (
        "No se puede eliminar al único integrante del proyecto"
        if esUltimo
        else (
            "No se puede eliminar un integrante con tareas activas asignadas"
            if tieneTareasAsignadas
            else "Eliminar integrante del equipo"
        )
    )

    claseContenedor = (
        "flex items-center justify-between p-2 rounded-lg border text-xs transition-colors "
        + (
            "bg-rose-50/80 border-rose-300 ring-1 ring-rose-200"
            if estaEnConfirmacion
            else "bg-white border-slate-100 shadow-sm"
        )
    )

    return html.div(
        {
            "id": f"item-integrante-{integrante.cedula}",
            "className": claseContenedor,
        },
        html.div(
            {"className": "flex items-center space-x-2.5 min-w-0"},
            html.div(
                {
                    "className": (
                        "w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 font-bold "
                        "text-[10px] flex items-center justify-center flex-shrink-0"
                    )
                },
                iniciales,
            ),
            html.div(
                {"className": "min-w-0"},
                html.p(
                    {
                        "id": f"nombre-integrante-{integrante.cedula}",
                        "className": "font-semibold text-slate-800 truncate",
                        "title": integrante.nombre,
                    },
                    integrante.nombre,
                ),
                html.div(
                    {
                        "className": "flex items-center space-x-1.5 text-[10px] text-slate-400"
                    },
                    html.span(
                        {
                            "id": f"cargo-integrante-{integrante.cedula}",
                            "className": "truncate max-w-[120px] text-slate-500",
                        },
                        integrante.cargo.value,
                    ),
                    html.span("•"),
                    html.span(
                        {
                            "id": f"cedula-integrante-{integrante.cedula}",
                            "className": "font-mono text-[9px]",
                        },
                        integrante.cedula,
                    ),
                ),
            ),
        ),
        html.button(
            {
                "id": f"btn-eliminar-integrante-{integrante.cedula}",
                "onClick": lambda e, c=integrante.cedula: alEliminar(c),
                "className": (
                    "p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors "
                    + (
                        "opacity-40 cursor-not-allowed"
                        if esUltimo or tieneTareasAsignadas
                        else ""
                    )
                ),
                "title": tituloBoton,
            },
            "✕",
        ),
    )


def renderizarConfirmacionEliminarIntegrante(
    integrante: Integrante,
    alConfirmar: Callable[[], None],
    alCancelar: Callable[[], None],
) -> VdomDict:
    """Renderiza el cuadro de confirmacion previa para eliminar un integrante del equipo."""
    return html.div(
        {
            "id": f"confirmacion-eliminar-integrante-{integrante.cedula}",
            "className": (
                "p-3 rounded-xl bg-rose-50 border border-rose-200 shadow-sm space-y-2 mt-2 "
                "animate-in fade-in duration-150"
            ),
        },
        html.div(
            {"className": "flex items-start space-x-2"},
            html.span(
                {"className": "text-rose-600 font-bold text-xs leading-none mt-0.5"},
                "⚠️",
            ),
            html.div(
                {"className": "text-xs text-rose-900"},
                html.p(
                    {"className": "font-semibold leading-tight"},
                    "¿Eliminar integrante del equipo?",
                ),
                html.p(
                    {"className": "text-[11px] text-rose-700 mt-1 leading-tight"},
                    f"¿Deseas remover a {integrante.nombre} ({integrante.cargo.value}) de este proyecto?",
                ),
            ),
        ),
        html.div(
            {"className": "flex items-center justify-end space-x-2 pt-1"},
            html.button(
                {
                    "id": f"btn-cancelar-eliminar-{integrante.cedula}",
                    "onClick": lambda e: alCancelar(),
                    "className": (
                        "px-2.5 py-1 text-xs text-slate-600 hover:text-slate-800 "
                        "bg-white border border-slate-200 rounded font-medium transition-colors"
                    ),
                },
                "Cancelar",
            ),
            html.button(
                {
                    "id": f"btn-confirmar-eliminar-{integrante.cedula}",
                    "onClick": lambda e: alConfirmar(),
                    "className": (
                        "px-3 py-1 bg-rose-600 text-white rounded text-xs font-semibold "
                        "hover:bg-rose-700 shadow-sm transition-colors"
                    ),
                },
                "Confirmar",
            ),
        ),
    )


def renderizarFormularioNuevoIntegrante(
    cedula: str,
    nombre: str,
    cargo: str,
    errores: dict[str, str],
    alCambiarCedula: Callable[[str], None],
    alCambiarNombre: Callable[[str], None],
    alCambiarCargo: Callable[[str], None],
    alGuardar: Callable[[], None],
    alCancelar: Callable[[], None],
) -> VdomDict:
    """Renderiza el formulario interactivo para registrar un nuevo integrante del proyecto."""
    cargosDisponibles = tuple(c.value for c in CargoIntegrante)

    return html.div(
        {
            "id": "formulario-nuevo-integrante",
            "className": "p-3 rounded-xl bg-white border-2 border-indigo-400 shadow-sm space-y-2.5 mt-2",
        },
        html.div(
            {"className": "flex items-center justify-between"},
            html.span(
                {
                    "className": "text-[11px] font-bold text-indigo-700 uppercase tracking-wider"
                },
                "Nuevo Integrante",
            ),
            html.button(
                {
                    "onClick": lambda e: alCancelar(),
                    "className": "text-slate-400 hover:text-slate-600 text-xs font-bold",
                },
                "✕",
            ),
        ),
        # Campo Cedula
        html.div(
            {"className": "space-y-0.5"},
            html.label(
                {
                    "className": "text-[10px] font-semibold text-slate-600 uppercase tracking-wider"
                },
                "Cédula (10 dígitos)",
            ),
            html.input(
                {
                    "id": "input-cedula-integrante",
                    "type": "text",
                    "placeholder": "Ej: 0928374651",
                    "value": cedula,
                    "onChange": lambda e: alCambiarCedula(e["target"]["value"]),
                    "className": (
                        f"{INPUT_ERROR if 'cedula' in errores else INPUT_TEXTO} text-xs py-1"
                    ),
                    "maxLength": 10,
                }
            ),
            html.span(
                {
                    "id": "error-cedula-integrante",
                    "className": TEXTO_ERROR_FORMULARIO
                    if "cedula" in errores
                    else "hidden",
                },
                errores.get("cedula", ""),
            ),
        ),
        # Campo Nombre
        html.div(
            {"className": "space-y-0.5"},
            html.label(
                {
                    "className": "text-[10px] font-semibold text-slate-600 uppercase tracking-wider"
                },
                "Nombre Completo",
            ),
            html.input(
                {
                    "id": "input-nombre-integrante",
                    "type": "text",
                    "placeholder": "Ej: Carlos Bernabé",
                    "value": nombre,
                    "onChange": lambda e: alCambiarNombre(e["target"]["value"]),
                    "className": (
                        f"{INPUT_ERROR if 'nombre' in errores else INPUT_TEXTO} text-xs py-1"
                    ),
                    "maxLength": 80,
                }
            ),
            html.span(
                {
                    "id": "error-nombre-integrante",
                    "className": TEXTO_ERROR_FORMULARIO
                    if "nombre" in errores
                    else "hidden",
                },
                errores.get("nombre", ""),
            ),
        ),
        # Campo Cargo
        html.div(
            {"className": "space-y-0.5"},
            html.label(
                {
                    "className": "text-[10px] font-semibold text-slate-600 uppercase tracking-wider"
                },
                "Cargo / Rol",
            ),
            html.select(
                {
                    "id": "select-cargo-integrante",
                    "value": cargo,
                    "onChange": lambda e: alCambiarCargo(e["target"]["value"]),
                    "className": f"{INPUT_TEXTO} text-xs py-1 bg-white",
                },
                [html.option({"key": c, "value": c}, c) for c in cargosDisponibles],
            ),
        ),
        # Botones de Accion
        html.div(
            {"className": "flex items-center justify-end space-x-2 pt-1"},
            html.button(
                {
                    "id": "btn-cancelar-integrante",
                    "onClick": lambda e: alCancelar(),
                    "className": "px-2.5 py-1 text-xs text-slate-600 hover:text-slate-800 rounded",
                },
                "Cancelar",
            ),
            html.button(
                {
                    "id": "btn-guardar-integrante",
                    "onClick": lambda e: alGuardar(),
                    "className": "px-3 py-1 bg-indigo-600 text-white rounded text-xs font-semibold hover:bg-indigo-700 shadow-sm",
                },
                "Agregar",
            ),
        ),
    )


def renderizarSeccionEquipo(
    proyecto: Proyecto,
    modoNuevoIntegrante: bool,
    cedulaAEliminar: str,
    cedulaForm: str,
    nombreForm: str,
    cargoForm: str,
    erroresForm: dict[str, str],
    alIniciarNuevoIntegrante: Callable[[], None],
    alCambiarCedula: Callable[[str], None],
    alCambiarNombre: Callable[[str], None],
    alCambiarCargo: Callable[[str], None],
    alGuardarIntegrante: Callable[[], None],
    alCancelarIntegrante: Callable[[], None],
    alSolicitarEliminarIntegrante: Callable[[str], None],
    alConfirmarEliminarIntegrante: Callable[[str], None],
    alCancelarEliminarIntegrante: Callable[[], None],
) -> VdomDict:
    """Renderiza la seccion inferior de gestion del equipo activo."""
    todasLasTareas: tuple[Tarea, ...] = tuple(
        t for paq in proyecto.paquetes for t in paq.tareas
    )
    esUltimo = len(proyecto.integrantes) <= 1
    integranteAEliminar = next(
        (i for i in proyecto.integrantes if i.cedula == cedulaAEliminar),
        None,
    )

    filasIntegrantes = [
        renderizarItemIntegrante(
            integrante=integ,
            esUltimo=esUltimo,
            tieneTareasAsignadas=any(
                t.activo
                and t.cedulaResponsable.esAlguno()
                and t.cedulaResponsable.obtenerValor() == integ.cedula
                for t in todasLasTareas
            ),
            alEliminar=alSolicitarEliminarIntegrante,
            estaEnConfirmacion=integ.cedula == cedulaAEliminar,
        )
        for integ in proyecto.integrantes
    ]

    return html.section(
        {
            "id": "seccion-equipo-sidebar",
            "className": "mt-auto p-4 border-t border-slate-200 bg-slate-50 space-y-3",
        },
        html.div(
            {"className": "flex items-center justify-between"},
            html.div(
                {"className": "flex items-center space-x-1.5"},
                html.span(
                    {
                        "className": "text-xs font-bold text-slate-700 uppercase tracking-wider"
                    },
                    "Equipo del Proyecto",
                ),
                html.span(
                    {
                        "id": "conteo-equipo-sidebar",
                        "className": "px-1.5 py-0.2 rounded-full bg-slate-200 text-slate-700 text-[10px] font-bold",
                    },
                    str(len(proyecto.integrantes)),
                ),
            ),
            html.button(
                {
                    "id": "btn-abrir-formulario-integrante",
                    "onClick": lambda e: alIniciarNuevoIntegrante(),
                    "className": (
                        "text-xs text-indigo-600 hover:text-indigo-800 font-semibold "
                        "hover:underline focus:outline-none"
                    ),
                },
                "+ Agregar",
            ),
        ),
        html.div(
            {"id": "lista-integrantes-sidebar", "className": "space-y-1.5"},
            *filasIntegrantes,
        ),
        (
            renderizarConfirmacionEliminarIntegrante(
                integrante=integranteAEliminar,
                alConfirmar=lambda c=cedulaAEliminar: alConfirmarEliminarIntegrante(c),
                alCancelar=alCancelarEliminarIntegrante,
            )
            if integranteAEliminar is not None
            else (
                renderizarFormularioNuevoIntegrante(
                    cedula=cedulaForm,
                    nombre=nombreForm,
                    cargo=cargoForm,
                    errores=erroresForm,
                    alCambiarCedula=alCambiarCedula,
                    alCambiarNombre=alCambiarNombre,
                    alCambiarCargo=alCambiarCargo,
                    alGuardar=alGuardarIntegrante,
                    alCancelar=alCancelarIntegrante,
                )
                if modoNuevoIntegrante
                else html.div()
            )
        ),
    )


# ==============================================================================
# COMPONENTE STATEFUL REACTPY (barraLateralEdt)
# ==============================================================================


@component
def barraLateralEdt(
    proyecto: Proyecto,
    idPaqueteSeleccionado: str,
    alSeleccionarPaquete: Callable[[str], None],
    alAgregarPaquete: Callable[[PaqueteTrabajo], None],
    alRenombrarPaquete: Callable[[str, str], None],
    alEliminarPaquete: Callable[[str], None],
    alVolverInicio: Callable[[], None],
    alAbrirMetricas: Callable[[], None],
    alAgregarIntegrante: Callable[[Integrante], None],
    alEliminarIntegrante: Callable[[str], None],
) -> VdomDict:
    """Componente ReactPy de la barra lateral de navegacion EDT y equipo del proyecto."""
    # -------------------------------------------------------------------------
    # Estados locales interactivos
    # -------------------------------------------------------------------------
    modoNuevoPaquete, setModoNuevoPaquete = use_state(False)
    nombreNuevoPaquete, setNombreNuevoPaquete = use_state("")
    errorNuevoPaquete, setErrorNuevoPaquete = use_state("")

    paqueteEnEdicion, setPaqueteEnEdicion = use_state("")
    nombreEdicionPaquete, setNombreEdicionPaquete = use_state("")
    errorEdicionPaquete, setErrorEdicionPaquete = use_state("")

    idPaqueteAEliminar, setIdPaqueteAEliminar = use_state("")

    modoNuevoIntegrante, setModoNuevoIntegrante = use_state(False)
    cedulaNuevoIntegrante, setCedulaNuevoIntegrante = use_state("")
    nombreNuevoIntegrante, setNombreNuevoIntegrante = use_state("")
    cargoNuevoIntegrante, setCargoNuevoIntegrante = use_state(
        CargoIntegrante.DESARROLLADOR_FULLSTACK.value
    )
    erroresNuevoIntegrante, setErroresNuevoIntegrante = use_state({})

    cedulaIntegranteAEliminar, setCedulaIntegranteAEliminar = use_state("")

    alertaContextual, setAlertaContextual = use_state("")

    # -------------------------------------------------------------------------
    # Manejadores de eventos de Paquetes
    # -------------------------------------------------------------------------
    def iniciarCreacionPaquete() -> None:
        setAlertaContextual("")
        setIdPaqueteAEliminar("")
        setPaqueteEnEdicion("")
        setNombreNuevoPaquete("")
        setErrorNuevoPaquete("")
        setModoNuevoPaquete(True)

    def cancelarCreacionPaquete() -> None:
        setModoNuevoPaquete(False)
        setNombreNuevoPaquete("")
        setErrorNuevoPaquete("")

    def confirmarCreacionPaquete() -> None:
        nombresExistentes = tuple(p.nombre for p in proyecto.paquetes)
        res = validarNombrePaquete(nombreNuevoPaquete, nombresExistentes)
        if res.esFallo():
            setErrorNuevoPaquete(res.error.mensaje)
            return

        nombreValido = res.obtenerValor()
        nuevoId = generarIdPaqueteSecuencial(proyecto.paquetes)
        nuevoPaquete = PaqueteTrabajo(
            idPaquete=nuevoId,
            idProyecto=proyecto.idProyecto,
            nombre=nombreValido,
            tareas=(),
        )
        setModoNuevoPaquete(False)
        setNombreNuevoPaquete("")
        setErrorNuevoPaquete("")
        alAgregarPaquete(nuevoPaquete)

    def iniciarRenombradoPaquete(paquete: PaqueteTrabajo) -> None:
        setAlertaContextual("")
        setIdPaqueteAEliminar("")
        setModoNuevoPaquete(False)
        setPaqueteEnEdicion(paquete.idPaquete)
        setNombreEdicionPaquete(paquete.nombre)
        setErrorEdicionPaquete("")

    def cancelarRenombradoPaquete() -> None:
        setPaqueteEnEdicion("")
        setNombreEdicionPaquete("")
        setErrorEdicionPaquete("")

    def confirmarRenombradoPaquete() -> None:
        otrosNombres = tuple(
            p.nombre for p in proyecto.paquetes if p.idPaquete != paqueteEnEdicion
        )
        res = validarNombrePaquete(nombreEdicionPaquete, otrosNombres)
        if res.esFallo():
            setErrorEdicionPaquete(res.error.mensaje)
            return

        nombreValido = res.obtenerValor()
        paqueteId = paqueteEnEdicion
        setPaqueteEnEdicion("")
        setNombreEdicionPaquete("")
        setErrorEdicionPaquete("")
        alRenombrarPaquete(paqueteId, nombreValido)

    def solicitarEliminarPaquete(paquete: PaqueteTrabajo) -> None:
        setModoNuevoPaquete(False)
        setPaqueteEnEdicion("")
        # Validacion EARS-03.7: Bloquear si contiene tareas asociadas
        res = validarEliminacionPaquete(paquete)
        if res.esFallo():
            setAlertaContextual(res.error.mensaje)
            setIdPaqueteAEliminar("")
            return

        # EARS-03.6: Si no contiene tareas, pedir confirmacion antes de eliminar
        setAlertaContextual("")
        setIdPaqueteAEliminar(paquete.idPaquete)

    def confirmarEliminarPaquete(idPaquete: str) -> None:
        setIdPaqueteAEliminar("")
        alEliminarPaquete(idPaquete)

    def cancelarEliminarPaquete() -> None:
        setIdPaqueteAEliminar("")

    # -------------------------------------------------------------------------
    # Manejadores de eventos de Integrantes
    # -------------------------------------------------------------------------
    def iniciarCreacionIntegrante() -> None:
        setAlertaContextual("")
        setCedulaIntegranteAEliminar("")
        setCedulaNuevoIntegrante("")
        setNombreNuevoIntegrante("")
        setCargoNuevoIntegrante(CargoIntegrante.DESARROLLADOR_FULLSTACK.value)
        setErroresNuevoIntegrante({})
        setModoNuevoIntegrante(True)

    def cancelarCreacionIntegrante() -> None:
        setModoNuevoIntegrante(False)
        setCedulaNuevoIntegrante("")
        setNombreNuevoIntegrante("")
        setErroresNuevoIntegrante({})

    def confirmarCreacionIntegrante() -> None:
        errores: dict[str, str] = {}
        cedulasExistentes = tuple(i.cedula for i in proyecto.integrantes)

        resCedula = validarCedula(cedulaNuevoIntegrante, cedulasExistentes)
        if resCedula.esFallo():
            errores["cedula"] = resCedula.error.mensaje

        resNombre = validarNombreIntegrante(nombreNuevoIntegrante)
        if resNombre.esFallo():
            errores["nombre"] = resNombre.error.mensaje

        if errores:
            setErroresNuevoIntegrante(errores)
            return

        nuevoIntegrante = Integrante(
            cedula=resCedula.obtenerValor(),
            idProyecto=proyecto.idProyecto,
            nombre=resNombre.obtenerValor(),
            cargo=CargoIntegrante(cargoNuevoIntegrante),
        )
        setModoNuevoIntegrante(False)
        setCedulaNuevoIntegrante("")
        setNombreNuevoIntegrante("")
        setErroresNuevoIntegrante({})
        alAgregarIntegrante(nuevoIntegrante)

    def solicitarEliminarIntegrante(cedula: str) -> None:
        setModoNuevoIntegrante(False)
        todasLasTareas = tuple(t for paq in proyecto.paquetes for t in paq.tareas)
        # Validacion EARS-03.8: Bloquear si es el unico o si tiene tareas activas
        res = validarEliminacionIntegrante(cedula, proyecto.integrantes, todasLasTareas)
        if res.esFallo():
            setAlertaContextual(res.error.mensaje)
            setCedulaIntegranteAEliminar("")
            return

        setAlertaContextual("")
        setCedulaIntegranteAEliminar(cedula)

    def confirmarEliminarIntegrante(cedula: str) -> None:
        setCedulaIntegranteAEliminar("")
        alEliminarIntegrante(cedula)

    def cancelarEliminarIntegrante() -> None:
        setCedulaIntegranteAEliminar("")

    # -------------------------------------------------------------------------
    # Ensamblado VDOM del Panel Lateral
    # -------------------------------------------------------------------------
    tienePaquetes = len(proyecto.paquetes) > 0

    elementosPaquetes: list[VdomDict] = []
    if modoNuevoPaquete:
        elementosPaquetes.append(
            renderizarFilaNuevoPaquete(
                nombre=nombreNuevoPaquete,
                error=errorNuevoPaquete,
                alCambiarNombre=setNombreNuevoPaquete,
                alGuardar=confirmarCreacionPaquete,
                alCancelar=cancelarCreacionPaquete,
            )
        )

    for paq in proyecto.paquetes:
        if paq.idPaquete == paqueteEnEdicion:
            elementosPaquetes.append(
                renderizarFilaRenombrarPaquete(
                    idPaquete=paq.idPaquete,
                    nombre=nombreEdicionPaquete,
                    error=errorEdicionPaquete,
                    alCambiarNombre=setNombreEdicionPaquete,
                    alGuardar=confirmarRenombradoPaquete,
                    alCancelar=cancelarRenombradoPaquete,
                )
            )
        elif paq.idPaquete == idPaqueteAEliminar:
            elementosPaquetes.append(
                renderizarConfirmacionEliminarPaquete(
                    paquete=paq,
                    alConfirmar=lambda pid=paq.idPaquete: confirmarEliminarPaquete(pid),
                    alCancelar=cancelarEliminarPaquete,
                )
            )
        else:
            elementosPaquetes.append(
                renderizarItemPaquete(
                    paquete=paq,
                    estaSeleccionado=paq.idPaquete == idPaqueteSeleccionado,
                    alSeleccionarPaquete=alSeleccionarPaquete,
                    alIniciarRenombrado=iniciarRenombradoPaquete,
                    alSolicitarEliminar=solicitarEliminarPaquete,
                )
            )

    return html.aside(
        {
            "id": "panel-lateral-edt-sidebar",
            "className": (
                "w-80 flex-shrink-0 bg-slate-50 border-r border-slate-200 flex flex-col "
                "h-full overflow-y-auto select-none"
            ),
        },
        # 1. Encabezado con Navegacion y Metricas
        renderizarEncabezadoProyecto(
            proyecto=proyecto,
            alVolverInicio=alVolverInicio,
            alAbrirMetricas=alAbrirMetricas,
        ),
        # 2. Alerta Contextual para Acciones Bloqueadas
        renderizarAlertaContextual(
            mensaje=alertaContextual,
            alCerrar=lambda: setAlertaContextual(""),
        ),
        # 3. Seccion EDT / Paquetes de Trabajo
        html.div(
            {
                "id": "seccion-paquetes-edt",
                "className": "flex-1 overflow-y-auto py-3 space-y-1",
            },
            html.div(
                {"className": "flex items-center justify-between px-4 pb-2"},
                html.span(
                    {
                        "className": "text-xs font-bold text-slate-700 uppercase tracking-wider"
                    },
                    "Paquetes EDT",
                ),
                html.button(
                    {
                        "id": "btn-agregar-paquete-header",
                        "onClick": lambda e: iniciarCreacionPaquete(),
                        "className": (
                            "text-xs text-indigo-600 hover:text-indigo-800 font-semibold "
                            "hover:underline focus:outline-none"
                        ),
                    },
                    "+ Agregar",
                ),
            ),
            (
                html.div({"id": "lista-paquetes-edt"}, *elementosPaquetes)
                if tienePaquetes
                else renderizarEstadoVacioEdt(
                    alIniciarCreacionPaquete=iniciarCreacionPaquete
                )
            ),
        ),
        # 4. Seccion Equipo Activo
        renderizarSeccionEquipo(
            proyecto=proyecto,
            modoNuevoIntegrante=modoNuevoIntegrante,
            cedulaAEliminar=cedulaIntegranteAEliminar,
            cedulaForm=cedulaNuevoIntegrante,
            nombreForm=nombreNuevoIntegrante,
            cargoForm=cargoNuevoIntegrante,
            erroresForm=erroresNuevoIntegrante,
            alIniciarNuevoIntegrante=iniciarCreacionIntegrante,
            alCambiarCedula=setCedulaNuevoIntegrante,
            alCambiarNombre=setNombreNuevoIntegrante,
            alCambiarCargo=setCargoNuevoIntegrante,
            alGuardarIntegrante=confirmarCreacionIntegrante,
            alCancelarIntegrante=cancelarCreacionIntegrante,
            alSolicitarEliminarIntegrante=solicitarEliminarIntegrante,
            alConfirmarEliminarIntegrante=confirmarEliminarIntegrante,
            alCancelarEliminarIntegrante=cancelarEliminarIntegrante,
        ),
    )
