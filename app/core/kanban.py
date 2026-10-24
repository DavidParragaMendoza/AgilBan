"""Módulo del motor de transiciones del tablero Kanban y trazabilidad de regresos.

Implementa los pilares 2, 6, 8 y 9 de programación funcional:
- Pattern matching estructural (match/case) exhaustivo para validar transiciones entre columnas.
- Inmutabilidad estricta generando nuevas tareas e historiales con replace.
- Ausencia explícita de valor con Opcion[str] para justificaciones de devolución.
- Manejo funcional de errores con Resultado[Tarea, ErrorTransicionKanban].
"""

from __future__ import annotations

import uuid
from dataclasses import replace

from app.domain.catalogos import EstadoKanban, PrioridadTarea
from app.domain.errores import ErrorTransicionKanban
from app.domain.modelos import Tarea, TransicionHistorial
from app.domain.monadas import Alguno, Exito, Fallo, Opcion, Resultado


def transicionesPermitidas(estadoActual: EstadoKanban) -> tuple[EstadoKanban, ...]:
    """Determina exhaustivamente mediante pattern matching las transiciones permitidas según el estado actual."""
    match estadoActual:
        case EstadoKanban.PENDIENTE:
            return (EstadoKanban.EN_PROGRESO,)
        case EstadoKanban.EN_PROGRESO:
            return (EstadoKanban.EN_REVISION, EstadoKanban.PENDIENTE)
        case EstadoKanban.EN_REVISION:
            return (EstadoKanban.TERMINADA, EstadoKanban.EN_PROGRESO)
        case EstadoKanban.TERMINADA:
            return (EstadoKanban.EN_PROGRESO,)


def esRetroceso(origen: EstadoKanban, destino: EstadoKanban) -> bool:
    """Evalúa funcionalmente mediante pattern matching si un cambio de estado constituye un retroceso en el flujo."""
    match (origen, destino):
        case (EstadoKanban.EN_PROGRESO, EstadoKanban.PENDIENTE):
            return True
        case (EstadoKanban.EN_REVISION, EstadoKanban.EN_PROGRESO):
            return True
        case (EstadoKanban.TERMINADA, EstadoKanban.EN_PROGRESO):
            return True
        case _:
            return False


def avanzarOTareasKanban(
    tarea: Tarea,
    nuevoEstado: EstadoKanban,
    comentario: Opcion[str],
    timestamp: str,
) -> Resultado[Tarea, ErrorTransicionKanban]:
    """Avanza o retrocede una tarea en el tablero Kanban garantizando justificación obligatoria en devoluciones."""
    permitidos = transicionesPermitidas(tarea.estado)
    if nuevoEstado not in permitidos:
        return Fallo(
            ErrorTransicionKanban(
                mensaje=f"Transición no permitida desde '{tarea.estado.value}' hacia '{nuevoEstado.value}'.",
                origen=tarea.estado,
                destino=nuevoEstado,
            )
        )

    if esRetroceso(tarea.estado, nuevoEstado):
        if comentario.esNinguno():
            return Fallo(
                ErrorTransicionKanban(
                    mensaje="Toda devolución o retroceso en el tablero exige una justificación obligatoria.",
                    origen=tarea.estado,
                    destino=nuevoEstado,
                )
            )

        textoComentario = comentario.obtenerValor().strip()
        if not (1 <= len(textoComentario) <= 300):
            return Fallo(
                ErrorTransicionKanban(
                    mensaje="El comentario de justificación debe contener entre 1 y 300 caracteres.",
                    origen=tarea.estado,
                    destino=nuevoEstado,
                )
            )

        comentarioFinal = Alguno(textoComentario)
        nuevoContador = tarea.contadorRegresos + 1
    else:
        comentarioFinal = comentario
        nuevoContador = tarea.contadorRegresos

    nuevaTransicion = TransicionHistorial(
        idTransicion=str(uuid.uuid4()),
        idTarea=tarea.idTarea,
        estadoOrigen=tarea.estado,
        estadoDestino=nuevoEstado,
        fechaHora=timestamp,
        comentario=comentarioFinal,
    )

    tareaActualizada = replace(
        tarea,
        estado=nuevoEstado,
        contadorRegresos=nuevoContador,
        historial=tarea.historial + (nuevaTransicion,),
    )
    return Exito(tareaActualizada)


def descartarTareaLogicamente(tarea: Tarea) -> Tarea:
    """Realiza el borrado lógico de una tarea en el tablero asignando inmutablemente activo = False."""
    return replace(tarea, activo=False)


def editarTarea(
    tarea: Tarea,
    nuevoTitulo: str,
    nuevaDesc: Opcion[str],
    nuevaPrioridad: PrioridadTarea,
    nuevoResp: Opcion[str],
    nuevaFecha: Opcion[str],
) -> Tarea:
    """Modifica los atributos editables de una tarea de forma inmutable, preservando identificadores, estado e historial."""
    return replace(
        tarea,
        titulo=nuevoTitulo.strip(),
        descripcion=nuevaDesc,
        prioridad=nuevaPrioridad,
        cedulaResponsable=nuevoResp,
        fechaObjetivo=nuevaFecha,
    )
