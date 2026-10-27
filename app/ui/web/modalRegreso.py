# ruff: noqa: N999
"""Modal emergente de justificación obligatoria para devoluciones en el tablero Kanban.

Implementa los requerimientos RF-05 y RF-06 (EARS-05.1 a EARS-05.4):
- Detección funcional del único destino de retroceso permitido mediante destinoRetroceso().
- Presentación de estado origen y destino como información de solo lectura (sin selector manual).
- Exigencia obligatoria de comentario de justificación de 1 a 300 caracteres no vacíos.
- Retención del modal y advertencia contextual ante intentos de confirmación inválidos.
- Cancelación limpia sin efectos secundarios sobre el modelo o base de datos.
"""

from __future__ import annotations

from collections.abc import Callable

from reactpy import component, html, use_state
from reactpy.types import VdomDict

from app.core.kanban import destinoRetroceso
from app.domain.modelos import Tarea
from app.ui.web.estilos import (
    BOTON_PRIMARIO,
    BOTON_SECUNDARIO,
    CONTENEDOR_MODAL,
    ENCABEZADO_MODAL,
    FONDO_MODAL_OVERLAY,
    INPUT_ERROR,
    INPUT_TEXTO,
    PIE_MODAL,
    TEXTO_ERROR_FORMULARIO,
    obtenerClaseEstadoKanban,
)


@component
def modalRegresoKanban(
    tarea: Tarea,
    alConfirmar: Callable[[str], None],
    alCancelar: Callable[[], None],
) -> VdomDict:
    """Componente modal interactivo para justificar y auditar el retroceso de una tarea."""
    comentario, setComentario = use_state("")
    error, setError = use_state("")

    opcionDestino = destinoRetroceso(tarea.estado)
    if opcionDestino.esNinguno():
        # Si la tarea no admite devolución (ej. Pendiente), el modal no se despliega
        return html.div({"id": "modal-regreso-invalido", "className": "hidden"})

    destino = opcionDestino.obtenerValor()
    claseOrigen = obtenerClaseEstadoKanban(tarea.estado)
    claseDestino = obtenerClaseEstadoKanban(destino)

    def manejarConfirmar(evento: dict | None = None) -> None:
        textoLimpio = comentario.strip()
        if not (1 <= len(textoLimpio) <= 300):
            setError(
                "El motivo de devolución es obligatorio y debe tener entre 1 y 300 caracteres "
                "(los espacios en blanco no son válidos)."
            )
            return

        setError("")
        alConfirmar(textoLimpio)

    def manejarCambioTexto(nuevoTexto: str) -> None:
        if len(nuevoTexto) <= 300:
            setComentario(nuevoTexto)
            if error:
                setError("")

    claseTextarea = INPUT_ERROR if error else INPUT_TEXTO

    return html.div(
        {
            "id": "modal-regreso-backdrop",
            "className": FONDO_MODAL_OVERLAY,
        },
        html.div(
            {
                "id": "modal-regreso-dialogo",
                "className": f"{CONTENEDOR_MODAL} max-w-lg",
            },
            # Encabezado del Modal
            html.div(
                {
                    "className": ENCABEZADO_MODAL,
                },
                html.div(
                    {"className": "flex items-center space-x-2.5"},
                    html.div(
                        {
                            "className": (
                                "w-9 h-9 rounded-xl bg-amber-50 text-amber-700 "
                                "flex items-center justify-center text-lg font-bold"
                            ),
                        },
                        "↩",
                    ),
                    html.div(
                        {"className": "space-y-0.5"},
                        html.div(
                            {"className": "flex items-center space-x-2"},
                            html.h3(
                                {
                                    "id": "titulo-modal-regreso",
                                    "className": "text-base font-bold text-slate-900 tracking-tight",
                                },
                                "Justificación de Devolución",
                            ),
                            html.span(
                                {
                                    "id": "id-tarea-modal-regreso",
                                    "className": "font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700",
                                },
                                tarea.idTarea,
                            ),
                        ),
                        html.p(
                            {"className": "text-xs text-slate-500"},
                            "Registro obligatorio de retroceso técnico para auditoría y trazabilidad ágil.",
                        ),
                    ),
                ),
                html.button(
                    {
                        "id": "btn-cerrar-modal-regreso",
                        "type": "button",
                        "onClick": lambda e: alCancelar(),
                        "className": "text-slate-400 hover:text-slate-600 font-bold text-sm px-1",
                        "title": "Cerrar sin guardar",
                    },
                    "✕",
                ),
            ),
            # Cuerpo del Modal
            html.div(
                {
                    "className": "p-6 space-y-4",
                },
                # Regla de Flujo / Advertencia
                html.div(
                    {
                        "className": (
                            "p-3 rounded-xl bg-amber-50/80 border border-amber-200 "
                            "text-amber-900 text-xs flex items-start space-x-2"
                        ),
                    },
                    html.span({"className": "text-sm"}, "⚠️"),
                    html.p(
                        {"className": "leading-relaxed font-medium"},
                        html.strong("Regla de Flujo: "),
                        "Este diálogo audita retrocesos Kanban y nunca permite saltos arbitrarios de estado.",
                    ),
                ),
                # Visualización Fija de Origen y Destino (Solo Lectura)
                html.div(
                    {
                        "id": "info-transicion-regreso",
                        "className": "p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5",
                    },
                    html.div(
                        {
                            "className": "flex items-center justify-between text-[11px] font-bold text-slate-500 uppercase tracking-wider"
                        },
                        html.span("Destino Único Calculado Automáticamente"),
                        html.span(
                            {
                                "className": "text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full text-[10px]"
                            },
                            "🔒 Solo lectura",
                        ),
                    ),
                    html.div(
                        {"className": "flex items-center space-x-3 pt-1"},
                        html.div(
                            {"className": "space-y-0.5"},
                            html.span(
                                {
                                    "className": "text-[10px] text-slate-400 font-medium block"
                                },
                                "Origen:",
                            ),
                            html.span(
                                {
                                    "id": "badge-origen-modal-regreso",
                                    "className": claseOrigen,
                                },
                                tarea.estado.value,
                            ),
                        ),
                        html.span(
                            {"className": "text-slate-400 font-bold text-base mt-2"},
                            "→",
                        ),
                        html.div(
                            {"className": "space-y-0.5"},
                            html.span(
                                {
                                    "className": "text-[10px] text-slate-400 font-medium block"
                                },
                                "Destino:",
                            ),
                            html.span(
                                {
                                    "id": "badge-destino-modal-regreso",
                                    "className": claseDestino,
                                },
                                destino.value,
                            ),
                        ),
                    ),
                ),
                # Título de la tarea auditada
                html.div(
                    {"className": "space-y-1"},
                    html.span(
                        {
                            "className": "text-[11px] font-semibold text-slate-500 uppercase tracking-wider"
                        },
                        "Tarea sujeta a devolución:",
                    ),
                    html.p(
                        {
                            "id": "titulo-tarea-modal-regreso",
                            "className": "text-sm font-semibold text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-200",
                        },
                        tarea.titulo,
                    ),
                ),
                # Campo de Justificación Obligatoria
                html.div(
                    {"className": "space-y-1.5"},
                    html.div(
                        {"className": "flex items-center justify-between"},
                        html.label(
                            {
                                "id": "label-motivo-regreso",
                                "className": "text-xs font-bold text-slate-700 uppercase tracking-wider",
                            },
                            "Motivo Obligatorio de Retroceso *",
                        ),
                        html.span(
                            {
                                "id": "contador-caracteres-regreso",
                                "className": "text-xs font-mono text-slate-400",
                            },
                            f"{len(comentario)} / 300",
                        ),
                    ),
                    html.textarea(
                        {
                            "id": "input-motivo-regreso",
                            "rows": 3,
                            "value": comentario,
                            "placeholder": "Explica detalladamente la justificación técnica del retroceso...",
                            "onChange": lambda e: manejarCambioTexto(
                                e["target"]["value"]
                            ),
                            "className": f"{claseTextarea} text-xs leading-relaxed resize-none",
                            "maxLength": 300,
                            "autoFocus": True,
                        }
                    ),
                    html.span(
                        {
                            "id": "error-motivo-regreso",
                            "className": TEXTO_ERROR_FORMULARIO if error else "hidden",
                        },
                        error,
                    ),
                ),
                # Nota de trazabilidad legal
                html.p(
                    {
                        "className": "text-[11px] text-slate-500 leading-relaxed bg-slate-50 p-2 rounded-lg border border-slate-100"
                    },
                    f"Al confirmar, el contador de regresos se incrementará a {tarea.contadorRegresos + 1} "
                    "y se registrará una transición inmutable con fecha y motivo en la bitácora histórica.",
                ),
            ),
            # Pie de Acciones
            html.div(
                {
                    "className": PIE_MODAL,
                },
                html.button(
                    {
                        "id": "btn-cancelar-regreso",
                        "type": "button",
                        "onClick": lambda e: alCancelar(),
                        "className": BOTON_SECUNDARIO,
                    },
                    "Cancelar",
                ),
                html.button(
                    {
                        "id": "btn-confirmar-regreso",
                        "type": "button",
                        "onClick": manejarConfirmar,
                        "className": f"{BOTON_PRIMARIO} bg-amber-600 hover:bg-amber-700 focus:ring-amber-500",
                    },
                    "↩ Confirmar Devolución",
                ),
            ),
        ),
    )
