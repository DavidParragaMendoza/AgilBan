"""Módulo de filtros analíticos, funciones de orden superior, clausuras y lambdas.

Implementa los pilares 1, 3, 4, 5, 6 y 8 de programación funcional:
- Del cómo al qué: transformaciones declarativas con comprensiones de tuplas.
- Funciones de Orden Superior (HOF): filtrarTareas aplica un predicado Callable[[Tarea], bool].
- Expresiones Lambda: criterios inline puros para ordenamiento jerárquico y cronológico.
- Closures (Clausuras): crearCriterioFiltro encapsula parámetros en el ámbito léxico retornado.
- Inmutabilidad estricta: operaciones sobre tuplas sin efectos colaterales.
- Ausencia de valor: evaluación explícita con el contenedor Opcion.
"""

from __future__ import annotations

from collections.abc import Callable

from app.domain.catalogos import EstadoKanban, PrioridadTarea
from app.domain.modelos import Tarea
from app.domain.monadas import Opcion

_PESOS_PRIORIDAD: dict[PrioridadTarea, int] = {
    PrioridadTarea.CRITICA: 4,
    PrioridadTarea.ALTA: 3,
    PrioridadTarea.MEDIA: 2,
    PrioridadTarea.BAJA: 1,
}


def crearCriterioFiltro(
    estado: Opcion[EstadoKanban],
    cedula: Opcion[str],
    prioridad: Opcion[PrioridadTarea],
    soloVencidas: bool,
    soloInactivas: bool,
    fechaReferencia: str,
) -> Callable[[Tarea], bool]:
    """Crea una clausura (closure) que encapsula criterios de búsqueda retornando un predicado puro."""

    def predicado(tarea: Tarea) -> bool:
        # Filtro de activación / borrado lógico
        if soloInactivas:
            if tarea.activo:
                return False
        else:
            if not tarea.activo:
                return False

        # Filtro por estado Kanban
        if estado.esAlguno() and tarea.estado != estado.obtenerValor():
            return False

        # Filtro por cédula de responsable
        if cedula.esAlguno() and tarea.cedulaResponsable != cedula:
            return False

        # Filtro por prioridad
        if prioridad.esAlguno() and tarea.prioridad != prioridad.obtenerValor():
            return False

        # Filtro de tareas vencidas (fechaObjetivo < fechaReferencia y no terminada)
        if soloVencidas:
            if tarea.fechaObjetivo.esNinguno():
                return False
            if tarea.estado == EstadoKanban.TERMINADA:
                return False
            if tarea.fechaObjetivo.obtenerValor() >= fechaReferencia:
                return False

        return True

    return predicado


def filtrarTareas(
    tareas: tuple[Tarea, ...],
    criterio: Callable[[Tarea], bool],
) -> tuple[Tarea, ...]:
    """Función de Orden Superior (HOF) que aplica declarativamente un predicado sobre una tupla de tareas."""
    return tuple(tarea for tarea in tareas if criterio(tarea))


def ordenarPorPrioridad(tareas: tuple[Tarea, ...]) -> tuple[Tarea, ...]:
    """Ordena descendentemente una colección de tareas usando una lambda para la jerarquía de prioridad."""
    return tuple(
        sorted(
            tareas,
            key=lambda t: _PESOS_PRIORIDAD.get(t.prioridad, 0),
            reverse=True,
        )
    )


def ordenarPorFecha(tareas: tuple[Tarea, ...]) -> tuple[Tarea, ...]:
    """Ordena ascendentemente una colección de tareas por fecha objetivo usando una expresión lambda."""
    return tuple(
        sorted(
            tareas,
            key=lambda t: (
                (0, t.fechaObjetivo.obtenerValor())
                if t.fechaObjetivo.esAlguno()
                else (1, "")
            ),
        )
    )
