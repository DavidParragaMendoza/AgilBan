"""Módulo de métricas analíticas, avance global y auditoría de cuellos de botella.

Implementa los pilares 1, 4, 6 y 7 de programación funcional:
- Del cómo al qué: transformaciones y conteos declarativos con comprensiones y sum.
- Expresiones Lambda: criterio inline en sorted para auditoría de cuellos de botella.
- Inmutabilidad estricta: preservación de tuplas y modelos sin efectos secundarios.
- Pureza y aislamiento I/O: cálculo puramente determinista sin dependencias externas.
"""

from __future__ import annotations

from app.domain.catalogos import EstadoKanban
from app.domain.modelos import Integrante, Tarea
from app.domain.monadas import Alguno


def calcularResumenTareas(tareas: tuple[Tarea, ...]) -> dict[str, int]:
    """Calcula cuantitativamente el total de tareas activas, desglose por columna Kanban y total de inactivas."""
    activas = [t for t in tareas if t.activo]
    inactivas = [t for t in tareas if not t.activo]

    return {
        "totalActivas": len(activas),
        "totalInactivas": len(inactivas),
        EstadoKanban.PENDIENTE.value: sum(
            1 for t in activas if t.estado == EstadoKanban.PENDIENTE
        ),
        EstadoKanban.EN_PROGRESO.value: sum(
            1 for t in activas if t.estado == EstadoKanban.EN_PROGRESO
        ),
        EstadoKanban.EN_REVISION.value: sum(
            1 for t in activas if t.estado == EstadoKanban.EN_REVISION
        ),
        EstadoKanban.TERMINADA.value: sum(
            1 for t in activas if t.estado == EstadoKanban.TERMINADA
        ),
    }


def calcularAvanceGlobal(tareas: tuple[Tarea, ...]) -> float:
    """Calcula el porcentaje de avance global del proyecto evitando división por cero si no hay activas."""
    activas = [t for t in tareas if t.activo]
    if not activas:
        return 0.0

    terminadas = sum(1 for t in activas if t.estado == EstadoKanban.TERMINADA)
    return round((terminadas / len(activas)) * 100.0, 2)


def calcularCargaIntegrantes(
    integrantes: tuple[Integrante, ...],
    tareas: tuple[Tarea, ...],
) -> dict[str, dict[str, int]]:
    """Calcula declarativamente las tareas activas asignadas y completadas para cada integrante."""
    return {
        integrante.cedula: {
            "asignadas": sum(
                1
                for t in tareas
                if t.activo and t.cedulaResponsable == Alguno(integrante.cedula)
            ),
            "terminadas": sum(
                1
                for t in tareas
                if t.activo
                and t.cedulaResponsable == Alguno(integrante.cedula)
                and t.estado == EstadoKanban.TERMINADA
            ),
        }
        for integrante in integrantes
    }


def auditarCuellosDeBotella(tareas: tuple[Tarea, ...]) -> tuple[Tarea, ...]:
    """Retorna las tareas activas con regresos acumulados ordenadas descendentemente por contador."""
    tareasConRegresos = [t for t in tareas if t.activo and t.contadorRegresos > 0]
    return tuple(
        sorted(
            tareasConRegresos,
            key=lambda t: t.contadorRegresos,
            reverse=True,
        )
    )
