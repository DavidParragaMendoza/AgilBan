"""Módulo de tipos de dominio inmutables, catálogos y errores."""

from app.domain.catalogos import (
    CargoIntegrante,
    EstadoKanban,
    EstadoPaquete,
    PrioridadTarea,
    TipoProyecto,
)
from app.domain.errores import (
    ErrorDominio,
    ErrorDuplicado,
    ErrorNoEncontrado,
    ErrorReglaNegocio,
    ErrorTransicionKanban,
    ErrorValidacion,
)
from app.domain.modelos import (
    EventoCreacionTarea,
    Integrante,
    PaqueteTrabajo,
    Proyecto,
    Tarea,
    TransicionHistorial,
)
from app.domain.monadas import Alguno, Exito, Fallo, Ninguno, Opcion, Resultado

__all__ = [
    "Alguno",
    "CargoIntegrante",
    "ErrorDominio",
    "ErrorDuplicado",
    "ErrorNoEncontrado",
    "ErrorReglaNegocio",
    "ErrorTransicionKanban",
    "ErrorValidacion",
    "EstadoKanban",
    "EstadoPaquete",
    "EventoCreacionTarea",
    "Exito",
    "Fallo",
    "Integrante",
    "Ninguno",
    "Opcion",
    "PaqueteTrabajo",
    "PrioridadTarea",
    "Proyecto",
    "Resultado",
    "Tarea",
    "TipoProyecto",
    "TransicionHistorial",
]
