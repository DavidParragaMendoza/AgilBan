# ruff: noqa: N999
"""Panel lateral deslizante (Side Drawer) para edición, autoguardado y descarte de tareas.

Implementa los requerimientos RF-06 y RF-10 (EARS-06.1 a EARS-06.6, EARS-10.1 a EARS-10.3):
- Panel deslizante estilo Notion desde la derecha sin ocultar completamente el tablero.
- Visualización de paquete de trabajo fijo y estado Kanban actual como metadatos.
- Cronología inmutable y no editable de creación de tarea y transiciones históricas.
- Soporte para tareas legacy sin fecha ni evento inventado (EARS-06.2).
- Autoguardado diferenciado: on_blur para título y descripción; on_change para prioridad, responsable y fecha.
- Indicadores visuales explícitos: 'Guardando…', '✓ Guardado' y 'No se pudo guardar' con botón de reintento.
- Separación estricta entre errores de validación de campos y fallos de persistencia.
- Descarte lógico con diálogo de confirmación y advertencia de trazabilidad para métricas.
- Protección de cierre ante borradores pendientes de persistencia o con errores.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from enum import Enum

from reactpy import component, html, use_state
from reactpy.types import VdomDict

from app.core.kanban import editarTarea
from app.domain.catalogos import PrioridadTarea
from app.domain.modelos import Integrante, Tarea
from app.domain.monadas import Alguno, Ninguno, Opcion
from app.ui.web.estilos import (
    BOTON_PELIGRO,
    BOTON_SECUNDARIO,
    FONDO_DRAWER_OVERLAY,
    INDICADOR_ERROR_PERSISTENCIA,
    INDICADOR_GUARDADO,
    INDICADOR_GUARDANDO,
    INPUT_ERROR,
    INPUT_TEXTO,
    LABEL_FORMULARIO,
    PANEL_LATERAL_DRAWER,
    TEXTO_ERROR_FORMULARIO,
    obtenerClaseEstadoKanban,
)


class EstadoGuardado(Enum):
    """Estado explícito del proceso de autoguardado reactivo."""

    GUARDANDO = "Guardando…"
    GUARDADO = "✓ Guardado"
    ERROR = "No se pudo guardar"


def _validarFecha(fechaStr: str) -> bool:
    """Valida si una cadena cumple con el formato ISO de fecha AAAA-MM-DD."""
    if not fechaStr.strip():
        return True
    try:
        datetime.strptime(fechaStr.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


@component
def panelEdicionTarea(
    tarea: Tarea,
    nombrePaquete: str,
    integrantes: tuple[Integrante, ...],
    alGuardarParcial: Callable[[Tarea], None],
    alDescartarTarea: Callable[[Tarea], None],
    alCerrar: Callable[[], None],
    estadoGuardado: EstadoGuardado = EstadoGuardado.GUARDADO,
    errorPersistencia: str = "",
) -> VdomDict:
    """Componente Side Drawer interactivo para edición y auditoría de tareas."""
    # -------------------------------------------------------------------------
    # 1. Estados Locales de Formulario y Validación
    # -------------------------------------------------------------------------
    descInicial = (
        tarea.descripcion.obtenerValor() if tarea.descripcion.esAlguno() else ""
    )
    respInicial = (
        tarea.cedulaResponsable.obtenerValor()
        if tarea.cedulaResponsable.esAlguno()
        else ""
    )
    fechaInicial = (
        tarea.fechaObjetivo.obtenerValor() if tarea.fechaObjetivo.esAlguno() else ""
    )

    tituloLocal, setTituloLocal = use_state(tarea.titulo)
    descripcionLocal, setDescripcionLocal = use_state(descInicial)
    prioridadLocal, setPrioridadLocal = use_state(tarea.prioridad)
    responsableLocal, setResponsableLocal = use_state(respInicial)
    fechaLocal, setFechaLocal = use_state(fechaInicial)

    errorTitulo, setErrorTitulo = use_state("")
    errorDescripcion, setErrorDescripcion = use_state("")
    errorFecha, setErrorFecha = use_state("")

    # Diálogos emergentes de confirmación
    mostrarConfirmacionDescarte, setMostrarConfirmacionDescarte = use_state(False)
    mostrarAdvertenciaCierre, setMostrarAdvertenciaCierre = use_state(False)

    # -------------------------------------------------------------------------
    # 2. Manejadores de Autoguardado Diferenciado
    # -------------------------------------------------------------------------
    def ejecutarGuardado(
        nuevoTitulo: str,
        nuevaDesc: str,
        nuevaPrio: PrioridadTarea,
        nuevaCedula: str,
        nuevaFechaStr: str,
    ) -> None:
        """Construye la entidad inmutable Tarea y delega la persistencia."""
        opcionDesc: Opcion[str] = (
            Alguno(nuevaDesc.strip()) if nuevaDesc.strip() else Ninguno()
        )
        opcionResp: Opcion[str] = Alguno(nuevaCedula) if nuevaCedula else Ninguno()
        opcionFecha: Opcion[str] = (
            Alguno(nuevaFechaStr.strip()) if nuevaFechaStr.strip() else Ninguno()
        )

        tareaModificada = editarTarea(
            tarea=tarea,
            nuevoTitulo=nuevoTitulo,
            nuevaDesc=opcionDesc,
            nuevaPrioridad=nuevaPrio,
            nuevoResp=opcionResp,
            nuevaFecha=opcionFecha,
        )
        alGuardarParcial(tareaModificada)

    # Autoguardado on_blur para Título (1-120 caracteres)
    def manejarBlurTitulo() -> None:
        texto = tituloLocal.strip()
        if not (1 <= len(texto) <= 120):
            setErrorTitulo(
                "El título es obligatorio y debe tener entre 1 y 120 caracteres."
            )
            return

        setErrorTitulo("")
        if texto != tarea.titulo:
            ejecutarGuardado(
                texto,
                descripcionLocal,
                prioridadLocal,
                responsableLocal,
                fechaLocal,
            )

    # Autoguardado on_blur para Descripción (hasta 1000 caracteres)
    def manejarBlurDescripcion() -> None:
        texto = descripcionLocal.strip()
        if len(texto) > 1000:
            setErrorDescripcion("La descripción no puede exceder los 1000 caracteres.")
            return

        setErrorDescripcion("")
        descActual = (
            tarea.descripcion.obtenerValor() if tarea.descripcion.esAlguno() else ""
        )
        if texto != descActual:
            ejecutarGuardado(
                tituloLocal,
                texto,
                prioridadLocal,
                responsableLocal,
                fechaLocal,
            )

    # Autoguardado on_change para Prioridad
    def manejarCambioPrioridad(nuevoValorStr: str) -> None:
        try:
            nuevaPrio = PrioridadTarea(nuevoValorStr)
        except ValueError:
            return

        setPrioridadLocal(nuevaPrio)
        if nuevaPrio != tarea.prioridad:
            ejecutarGuardado(
                tituloLocal,
                descripcionLocal,
                nuevaPrio,
                responsableLocal,
                fechaLocal,
            )

    # Autoguardado on_change para Responsable
    def manejarCambioResponsable(nuevaCedula: str) -> None:
        setResponsableLocal(nuevaCedula)
        respActual = (
            tarea.cedulaResponsable.obtenerValor()
            if tarea.cedulaResponsable.esAlguno()
            else ""
        )
        if nuevaCedula != respActual:
            ejecutarGuardado(
                tituloLocal,
                descripcionLocal,
                prioridadLocal,
                nuevaCedula,
                fechaLocal,
            )

    # Autoguardado on_change para Fecha Objetivo
    def manejarCambioFecha(nuevaFechaStr: str) -> None:
        setFechaLocal(nuevaFechaStr)
        if not _validarFecha(nuevaFechaStr):
            setErrorFecha("Formato de fecha inválido. Utilice AAAA-MM-DD.")
            return

        setErrorFecha("")
        fechaActual = (
            tarea.fechaObjetivo.obtenerValor() if tarea.fechaObjetivo.esAlguno() else ""
        )
        if nuevaFechaStr.strip() != fechaActual:
            ejecutarGuardado(
                tituloLocal,
                descripcionLocal,
                prioridadLocal,
                responsableLocal,
                nuevaFechaStr,
            )

    # -------------------------------------------------------------------------
    # 3. Control y Protección de Cierre
    # -------------------------------------------------------------------------
    hayErroresValidacion = bool(errorTitulo or errorDescripcion or errorFecha)
    hayFalloPersistencia = estadoGuardado == EstadoGuardado.ERROR
    hayCambiosSinGuardar = (
        tituloLocal.strip() != tarea.titulo
        or descripcionLocal.strip() != descInicial
        or prioridadLocal != tarea.prioridad
        or responsableLocal != respInicial
        or fechaLocal.strip() != fechaInicial
    )

    def solicitarCierre() -> None:
        if hayErroresValidacion or hayFalloPersistencia or hayCambiosSinGuardar:
            setMostrarAdvertenciaCierre(True)
        else:
            alCerrar()

    def descartarBorradorYCerrar() -> None:
        setMostrarAdvertenciaCierre(False)
        alCerrar()

    # Reintentar guardado manual ante error de persistencia
    def reintentarGuardado() -> None:
        if not errorTitulo and not errorDescripcion and not errorFecha:
            ejecutarGuardado(
                tituloLocal,
                descripcionLocal,
                prioridadLocal,
                responsableLocal,
                fechaLocal,
            )

    # -------------------------------------------------------------------------
    # 4. Construcción de Secciones Visuales
    # -------------------------------------------------------------------------
    # Indicador reactivo de estado de guardado
    indicadorVisual = html.div()
    if estadoGuardado == EstadoGuardado.GUARDANDO:
        indicadorVisual = html.div(
            {
                "id": "indicador-guardado-drawer",
                "className": INDICADOR_GUARDANDO,
            },
            html.span({"className": "animate-spin text-xs"}, "⏳"),
            html.span("Guardando…"),
        )
    elif estadoGuardado == EstadoGuardado.GUARDADO:
        indicadorVisual = html.div(
            {
                "id": "indicador-guardado-drawer",
                "className": INDICADOR_GUARDADO,
            },
            html.span("✓ Guardado"),
        )
    elif estadoGuardado == EstadoGuardado.ERROR:
        indicadorVisual = html.div(
            {
                "id": "indicador-guardado-drawer",
                "className": "flex items-center space-x-2",
            },
            html.span(
                {"className": INDICADOR_ERROR_PERSISTENCIA},
                "⚠️ No se pudo guardar",
            ),
            html.button(
                {
                    "id": "btn-reintentar-guardado",
                    "type": "button",
                    "onClick": lambda e: reintentarGuardado(),
                    "className": (
                        "px-2 py-0.5 rounded text-[11px] font-bold bg-rose-50 text-rose-700 "
                        "border border-rose-200 hover:bg-rose-100 transition-colors"
                    ),
                },
                "Reintentar",
            ),
        )

    # Cronología de Creación y Transiciones
    nodosHistorial: list[VdomDict] = []
    # Evento de Creación (EARS-06.2: sin inventar para tareas legacy)
    if tarea.eventoCreacion.esAlguno():
        ev = tarea.eventoCreacion.obtenerValor()
        nodosHistorial.append(
            html.li(
                {
                    "id": "evento-creacion-tarea-drawer",
                    "className": "relative pl-6 pb-4 border-l-2 border-indigo-200 last:border-0",
                },
                html.div(
                    {
                        "className": (
                            "absolute -left-1.5 top-0.5 w-3 h-3 rounded-full "
                            "bg-indigo-600 border-2 border-white shadow-sm"
                        ),
                    }
                ),
                html.div(
                    {"className": "space-y-0.5"},
                    html.div(
                        {"className": "flex items-center space-x-2"},
                        html.span(
                            {"className": "text-xs font-bold text-slate-800"},
                            "Creación inicial de la tarea",
                        ),
                        html.span(
                            {
                                "className": "px-1.5 py-0.2 rounded text-[10px] bg-indigo-50 text-indigo-700 font-semibold"
                            },
                            "Alta",
                        ),
                    ),
                    html.p(
                        {
                            "id": "fecha-creacion-tarea-drawer",
                            "className": "text-[11px] font-mono text-slate-400",
                        },
                        ev.fechaHora,
                    ),
                ),
            )
        )
    else:
        nodosHistorial.append(
            html.li(
                {
                    "id": "evento-creacion-legacy-drawer",
                    "className": "p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-500 italic",
                },
                "Registro histórico heredado: esta tarea no posee evento de alta original.",
            )
        )

    # Transiciones Históricas
    if len(tarea.historial) > 0:
        for i, tr in enumerate(tarea.historial):
            tieneMotivo = tr.comentario.esAlguno()
            motivoTexto = tr.comentario.obtenerValor() if tieneMotivo else ""
            nodosHistorial.append(
                html.li(
                    {
                        "id": f"transicion-historial-{i}",
                        "className": "relative pl-6 pb-4 border-l-2 border-slate-200 last:border-0",
                    },
                    html.div(
                        {
                            "className": (
                                "absolute -left-1.5 top-1 w-3 h-3 rounded-full "
                                + ("bg-amber-500" if tieneMotivo else "bg-slate-400")
                                + " border-2 border-white shadow-sm"
                            ),
                        }
                    ),
                    html.div(
                        {"className": "space-y-1"},
                        html.div(
                            {"className": "flex items-center space-x-1.5 text-xs"},
                            html.span(
                                {"className": "font-semibold text-slate-700"},
                                tr.estadoOrigen.value,
                            ),
                            html.span({"className": "text-slate-400 font-bold"}, "→"),
                            html.span(
                                {"className": "font-bold text-slate-900"},
                                tr.estadoDestino.value,
                            ),
                        ),
                        html.p(
                            {"className": "text-[11px] font-mono text-slate-400"},
                            tr.fechaHora,
                        ),
                        (
                            html.div(
                                {
                                    "className": (
                                        "p-2 rounded bg-amber-50 border border-amber-200 "
                                        "text-xs text-amber-900 mt-1 space-y-0.5"
                                    ),
                                },
                                html.span(
                                    {
                                        "className": "font-bold block text-[10px] uppercase text-amber-700"
                                    },
                                    "Motivo de devolución:",
                                ),
                                html.p({"className": "italic"}, f'"{motivoTexto}"'),
                            )
                            if tieneMotivo
                            else html.span()
                        ),
                    ),
                )
            )

    # Diálogo de confirmación para descarte lógico
    dialogoDescarte = html.div()
    if mostrarConfirmacionDescarte:
        dialogoDescarte = html.div(
            {
                "id": "confirmacion-descarte-tarea",
                "className": (
                    "p-4 rounded-xl bg-rose-50 border border-rose-200 space-y-3 "
                    "animate-in fade-in duration-150"
                ),
            },
            html.div(
                {"className": "flex items-start space-x-2.5"},
                html.span({"className": "text-lg"}, "⚠️"),
                html.div(
                    {"className": "space-y-1"},
                    html.h5(
                        {
                            "className": "text-xs font-bold text-rose-950 uppercase tracking-wider"
                        },
                        "¿Descartar esta tarea?",
                    ),
                    html.p(
                        {"className": "text-xs text-rose-800 leading-relaxed"},
                        "La tarea se retirará inmediatamente del tablero Kanban activo, pero se conservará de forma inmutable "
                        "en la base de datos para auditoría histórica y cálculo de métricas.",
                    ),
                ),
            ),
            html.div(
                {"className": "flex items-center justify-end space-x-2 pt-1"},
                html.button(
                    {
                        "id": "btn-cancelar-descarte-tarea",
                        "type": "button",
                        "onClick": lambda e: setMostrarConfirmacionDescarte(False),
                        "className": f"{BOTON_SECUNDARIO} text-xs py-1 px-3",
                    },
                    "Cancelar",
                ),
                html.button(
                    {
                        "id": "btn-confirmar-descarte-tarea",
                        "type": "button",
                        "onClick": lambda e: alDescartarTarea(tarea),
                        "className": f"{BOTON_PELIGRO} text-xs py-1 px-3",
                    },
                    "Confirmar Descarte",
                ),
            ),
        )

    # Diálogo de advertencia ante cierre con borrador pendiente
    dialogoAdvertenciaCierre = html.div()
    if mostrarAdvertenciaCierre:
        dialogoAdvertenciaCierre = html.div(
            {
                "id": "advertencia-cierre-drawer",
                "className": (
                    "p-4 rounded-xl bg-amber-50 border border-amber-200 space-y-3 "
                    "animate-in fade-in duration-150"
                ),
            },
            html.div(
                {"className": "flex items-start space-x-2"},
                html.span({"className": "text-lg"}, "⚠️"),
                html.div(
                    {"className": "space-y-1"},
                    html.h5(
                        {
                            "className": "text-xs font-bold text-amber-950 uppercase tracking-wider"
                        },
                        "Cambios pendientes de guardado",
                    ),
                    html.p(
                        {"className": "text-xs text-amber-800 leading-relaxed"},
                        "Existen modificaciones sin confirmar o errores de persistencia en el borrador. "
                        "Si cierras ahora, los cambios no guardados se descartarán.",
                    ),
                ),
            ),
            html.div(
                {"className": "flex items-center justify-end space-x-2 pt-1"},
                html.button(
                    {
                        "id": "btn-volver-edicion-drawer",
                        "type": "button",
                        "onClick": lambda e: setMostrarAdvertenciaCierre(False),
                        "className": f"{BOTON_SECUNDARIO} text-xs py-1 px-3",
                    },
                    "Volver a la edición",
                ),
                html.button(
                    {
                        "id": "btn-descartar-borrador-cerrar",
                        "type": "button",
                        "onClick": lambda e: descartarBorradorYCerrar(),
                        "className": f"{BOTON_PELIGRO} text-xs py-1 px-3 bg-amber-700 hover:bg-amber-800 focus:ring-amber-500",
                    },
                    "Descartar y Cerrar",
                ),
            ),
        )

    # -------------------------------------------------------------------------
    # 5. Ensamblado del Side Drawer (Estilo Notion)
    # -------------------------------------------------------------------------
    return html.div(
        {
            "id": "panel-edicion-tarea-contenedor",
        },
        # Fondo overlay semi-transparente
        html.div(
            {
                "id": "fondo-drawer-overlay",
                "onClick": lambda e: solicitarCierre(),
                "className": FONDO_DRAWER_OVERLAY,
            }
        ),
        # Panel lateral deslizante
        html.aside(
            {
                "id": "panel-edicion-tarea-drawer",
                "className": f"{PANEL_LATERAL_DRAWER} max-w-lg",
            },
            # Encabezado del Drawer
            html.header(
                {
                    "className": (
                        "px-6 py-4 border-b border-slate-100 flex items-center "
                        "justify-between bg-white flex-shrink-0"
                    ),
                },
                html.div(
                    {"className": "flex items-center space-x-3 min-w-0"},
                    html.span(
                        {
                            "id": "id-tarea-drawer",
                            "className": "font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700",
                        },
                        tarea.idTarea,
                    ),
                    indicadorVisual,
                ),
                html.button(
                    {
                        "id": "btn-cerrar-drawer-tarea",
                        "type": "button",
                        "onClick": lambda e: solicitarCierre(),
                        "className": "text-slate-400 hover:text-slate-600 font-bold text-base px-1.5 py-0.5 rounded hover:bg-slate-100",
                        "title": "Cerrar panel de edición",
                    },
                    "✕",
                ),
            ),
            # Alertas contextuales de cierre o fallo
            (
                html.div(
                    {
                        "id": "banner-error-persistencia-drawer",
                        "className": (
                            "mx-6 mt-3 p-3 rounded-lg bg-rose-50 border border-rose-200 "
                            "text-xs text-rose-800 flex items-center justify-between"
                        ),
                    },
                    html.span(
                        errorPersistencia
                        if errorPersistencia
                        else "Ocurrió un error al persistir los cambios."
                    ),
                    html.button(
                        {
                            "type": "button",
                            "onClick": lambda e: reintentarGuardado(),
                            "className": "font-bold text-rose-900 underline hover:no-underline ml-2",
                        },
                        "Reintentar",
                    ),
                )
                if hayFalloPersistencia
                else html.div()
            ),
            dialogoAdvertenciaCierre,
            dialogoDescarte,
            # Cuerpo de Campos y Metadatos (Scrollable)
            html.div(
                {
                    "className": "p-6 overflow-y-auto space-y-5 flex-1",
                },
                # Metadatos fijos: Paquete y Estado Kanban
                html.div(
                    {
                        "className": "p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between text-xs",
                    },
                    html.div(
                        {"className": "space-y-0.5"},
                        html.span(
                            {
                                "className": "text-[10px] text-slate-400 font-bold uppercase"
                            },
                            "Paquete EDT",
                        ),
                        html.p(
                            {
                                "id": "paquete-fijo-drawer",
                                "className": "font-semibold text-slate-800 truncate max-w-[180px]",
                            },
                            nombrePaquete,
                        ),
                    ),
                    html.div(
                        {"className": "space-y-0.5 text-right"},
                        html.span(
                            {
                                "className": "text-[10px] text-slate-400 font-bold uppercase"
                            },
                            "Columna Kanban",
                        ),
                        html.div(
                            {
                                "id": "estado-kanban-drawer",
                                "className": obtenerClaseEstadoKanban(tarea.estado),
                            },
                            tarea.estado.value,
                        ),
                    ),
                ),
                # Campo 1: Título de la Tarea (on_blur)
                html.div(
                    {"className": "space-y-1.5"},
                    html.label(
                        {"className": LABEL_FORMULARIO},
                        "Título de la Tarea *",
                    ),
                    html.input(
                        {
                            "id": "input-titulo-tarea-drawer",
                            "type": "text",
                            "value": tituloLocal,
                            "placeholder": "Título conciso de la tarea (1 a 120 caracteres)",
                            "onChange": lambda e: setTituloLocal(e["target"]["value"]),
                            "onBlur": lambda e: manejarBlurTitulo(),
                            "className": f"{INPUT_ERROR if errorTitulo else INPUT_TEXTO} text-xs font-semibold",
                            "maxLength": 120,
                        }
                    ),
                    (
                        html.span(
                            {
                                "id": "error-titulo-tarea-drawer",
                                "className": TEXTO_ERROR_FORMULARIO,
                            },
                            errorTitulo,
                        )
                        if errorTitulo
                        else html.span()
                    ),
                ),
                # Campo 2: Descripción (on_blur)
                html.div(
                    {"className": "space-y-1.5"},
                    html.div(
                        {"className": "flex items-center justify-between"},
                        html.label(
                            {"className": LABEL_FORMULARIO},
                            "Descripción Detallada",
                        ),
                        html.span(
                            {"className": "text-[11px] font-mono text-slate-400"},
                            f"{len(descripcionLocal)} / 1000",
                        ),
                    ),
                    html.textarea(
                        {
                            "id": "input-descripcion-tarea-drawer",
                            "rows": 4,
                            "value": descripcionLocal,
                            "placeholder": "Detalles técnicos, criterios de aceptación o notas de implementación...",
                            "onChange": lambda e: setDescripcionLocal(
                                e["target"]["value"]
                            ),
                            "onBlur": lambda e: manejarBlurDescripcion(),
                            "className": f"{INPUT_ERROR if errorDescripcion else INPUT_TEXTO} text-xs leading-relaxed resize-none",
                            "maxLength": 1000,
                        }
                    ),
                    (
                        html.span(
                            {
                                "id": "error-descripcion-tarea-drawer",
                                "className": TEXTO_ERROR_FORMULARIO,
                            },
                            errorDescripcion,
                        )
                        if errorDescripcion
                        else html.span()
                    ),
                ),
                # Fila de Prioridad y Responsable (on_change)
                html.div(
                    {"className": "grid grid-cols-2 gap-4"},
                    # Prioridad
                    html.div(
                        {"className": "space-y-1.5"},
                        html.label(
                            {"className": LABEL_FORMULARIO},
                            "Prioridad",
                        ),
                        html.select(
                            {
                                "id": "select-prioridad-tarea-drawer",
                                "value": prioridadLocal.value,
                                "onChange": lambda e: manejarCambioPrioridad(
                                    e["target"]["value"]
                                ),
                                "className": f"{INPUT_TEXTO} text-xs font-medium",
                            },
                            *[
                                html.option({"value": p.value}, p.value)
                                for p in PrioridadTarea
                            ],
                        ),
                    ),
                    # Responsable
                    html.div(
                        {"className": "space-y-1.5"},
                        html.label(
                            {"className": LABEL_FORMULARIO},
                            "Responsable",
                        ),
                        html.select(
                            {
                                "id": "select-responsable-tarea-drawer",
                                "value": responsableLocal,
                                "onChange": lambda e: manejarCambioResponsable(
                                    e["target"]["value"]
                                ),
                                "className": f"{INPUT_TEXTO} text-xs font-medium",
                            },
                            html.option({"value": ""}, "Sin asignar"),
                            *[
                                html.option(
                                    {"value": m.cedula},
                                    f"{m.nombre} ({m.cargo.value})",
                                )
                                for m in integrantes
                            ],
                        ),
                    ),
                ),
                # Campo Fecha Objetivo (on_change)
                html.div(
                    {"className": "space-y-1.5"},
                    html.label(
                        {"className": LABEL_FORMULARIO},
                        "Fecha Objetivo (AAAA-MM-DD)",
                    ),
                    html.input(
                        {
                            "id": "input-fecha-tarea-drawer",
                            "type": "text",
                            "value": fechaLocal,
                            "placeholder": "Ej: 2026-11-20",
                            "onChange": lambda e: manejarCambioFecha(
                                e["target"]["value"]
                            ),
                            "className": f"{INPUT_ERROR if errorFecha else INPUT_TEXTO} text-xs font-mono",
                            "maxLength": 10,
                        }
                    ),
                    (
                        html.span(
                            {
                                "id": "error-fecha-tarea-drawer",
                                "className": TEXTO_ERROR_FORMULARIO,
                            },
                            errorFecha,
                        )
                        if errorFecha
                        else html.span()
                    ),
                ),
                # Sección de Auditoría y Cronología (No editable)
                html.div(
                    {
                        "id": "cronologia-tarea-drawer",
                        "className": "pt-4 border-t border-slate-200 space-y-3",
                    },
                    html.div(
                        {"className": "flex items-center justify-between"},
                        html.h5(
                            {
                                "className": "text-xs font-bold text-slate-700 uppercase tracking-wider"
                            },
                            "Cronología de Auditoría",
                        ),
                        html.span(
                            {"className": "text-[10px] text-slate-400"},
                            f"{tarea.contadorRegresos} regresos auditados",
                        ),
                    ),
                    html.ul(
                        {
                            "id": "lista-transiciones-tarea-drawer",
                            "className": "space-y-1 mt-2",
                        },
                        *nodosHistorial,
                    ),
                ),
            ),
            # Pie del Drawer: Acción de Descarte Lógico
            html.footer(
                {
                    "className": (
                        "px-6 py-4 bg-slate-50 border-t border-slate-100 "
                        "flex items-center justify-between flex-shrink-0"
                    ),
                },
                html.button(
                    {
                        "id": "btn-descartar-tarea",
                        "type": "button",
                        "onClick": lambda e: setMostrarConfirmacionDescarte(True),
                        "className": (
                            "text-xs text-rose-600 hover:text-rose-800 font-semibold "
                            "flex items-center space-x-1.5 py-1 px-2 rounded hover:bg-rose-50 transition-colors"
                        ),
                    },
                    html.span("🗑️"),
                    html.span("Descartar Tarea"),
                ),
                html.button(
                    {
                        "id": "btn-cerrar-drawer-pie",
                        "type": "button",
                        "onClick": lambda e: solicitarCierre(),
                        "className": f"{BOTON_SECUNDARIO} text-xs py-1.5 px-4",
                    },
                    "Listo",
                ),
            ),
        ),
    )
