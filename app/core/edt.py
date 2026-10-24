"""Módulo de cálculo declarativo de la Estructura de Desglose del Trabajo (EDT).

Implementa los pilares 1 y 6 de programación funcional:
- Del cómo al qué: transformaciones y consultas declarativas sin acumuladores mutables.
- Inmutabilidad estricta: transformaciones puras generando nuevas versiones con replace.
"""

from __future__ import annotations

from dataclasses import replace

from app.domain.catalogos import EstadoKanban, EstadoPaquete
from app.domain.errores import ErrorDuplicado, ErrorNoEncontrado
from app.domain.modelos import PaqueteTrabajo, Proyecto, Tarea
from app.domain.monadas import Exito, Fallo, Resultado


def obtenerTareasActivas(paquete: PaqueteTrabajo) -> tuple[Tarea, ...]:
    """Filtra y retorna de forma declarativa las tareas activas (no descartadas) del paquete."""
    return tuple(tarea for tarea in paquete.tareas if tarea.activo)


def calcularEstadoPaquete(paquete: PaqueteTrabajo) -> EstadoPaquete:
    """Calcula declarativamente el estado derivado de un paquete según sus tareas activas."""
    tareasActivas = obtenerTareasActivas(paquete)
    if not tareasActivas:
        return EstadoPaquete.SIN_TAREAS

    if all(t.estado == EstadoKanban.PENDIENTE for t in tareasActivas):
        return EstadoPaquete.PENDIENTE

    if all(t.estado == EstadoKanban.TERMINADA for t in tareasActivas):
        return EstadoPaquete.TERMINADO

    return EstadoPaquete.EN_PROGRESO


def calcularAvancePaquete(paquete: PaqueteTrabajo) -> float:
    """Calcula el porcentaje de avance de un paquete protegiendo contra división por cero."""
    tareasActivas = obtenerTareasActivas(paquete)
    if not tareasActivas:
        return 0.0

    totalTerminadas = sum(
        1 for t in tareasActivas if t.estado == EstadoKanban.TERMINADA
    )
    return round((totalTerminadas / len(tareasActivas)) * 100.0, 2)


def agregarPaqueteAProyecto(
    proyecto: Proyecto, nuevoPaquete: PaqueteTrabajo
) -> Proyecto:
    """Retorna una nueva copia inmutable del proyecto con el paquete de trabajo anexado."""
    return replace(proyecto, paquetes=proyecto.paquetes + (nuevoPaquete,))


def renombrarPaquete(
    proyecto: Proyecto, idPaquete: str, nuevoNombre: str
) -> Resultado[Proyecto, ErrorDuplicado | ErrorNoEncontrado]:
    """Valida la existencia y unicidad del nuevo nombre para renombrar un paquete inmutablemente."""
    paqueteObjetivo = next(
        (p for p in proyecto.paquetes if p.idPaquete == idPaquete), None
    )
    if paqueteObjetivo is None:
        return Fallo(
            ErrorNoEncontrado(
                mensaje=f"No se encontró el paquete con identificador '{idPaquete}'.",
                entidad="PaqueteTrabajo",
                identificador=idPaquete,
            )
        )

    nombreLimpio = nuevoNombre.strip()
    nombreMinusculas = nombreLimpio.lower()
    otrosNombres = tuple(
        p.nombre.strip().lower() for p in proyecto.paquetes if p.idPaquete != idPaquete
    )

    if nombreMinusculas in otrosNombres:
        return Fallo(
            ErrorDuplicado(
                mensaje=f"Ya existe un paquete de trabajo con el nombre '{nombreLimpio}' en este proyecto.",
                entidad="PaqueteTrabajo",
                identificador=nombreLimpio,
            )
        )

    nuevosPaquetes = tuple(
        replace(p, nombre=nombreLimpio) if p.idPaquete == idPaquete else p
        for p in proyecto.paquetes
    )
    return Exito(replace(proyecto, paquetes=nuevosPaquetes))
