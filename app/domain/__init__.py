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
    "Exito",
    "Fallo",
    "Ninguno",
    "Opcion",
    "PrioridadTarea",
    "Resultado",
    "TipoProyecto",
]
