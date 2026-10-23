"""Jerarquía inmutable de errores tipados del dominio para AgilBan.

Todos los errores son tipos inmutables (@dataclass(frozen=True)) utilizados
como variantes de Fallo[E] dentro del contenedor monádico Resultado[T, E].
"""

from dataclasses import dataclass

from app.domain.catalogos import EstadoKanban


@dataclass(frozen=True)
class ErrorDominio(Exception):
    """Clase base inmutable para todos los errores tipados del dominio."""

    mensaje: str

    def __str__(self) -> str:
        return self.mensaje


@dataclass(frozen=True)
class ErrorValidacion(ErrorDominio):
    """Violación de formato, longitud o reglas de entrada de datos."""

    campo: str


@dataclass(frozen=True)
class ErrorDuplicado(ErrorDominio):
    """Conflicto de unicidad en identificadores o nombres dentro del dominio."""

    entidad: str
    identificador: str


@dataclass(frozen=True)
class ErrorNoEncontrado(ErrorDominio):
    """Búsqueda o referencia a una entidad inexistente."""

    entidad: str
    identificador: str


@dataclass(frozen=True)
class ErrorReglaNegocio(ErrorDominio):
    """Violación de invariantes de negocio del sistema."""

    codigo: str


@dataclass(frozen=True)
class ErrorTransicionKanban(ErrorDominio):
    """Transición no autorizada entre columnas o devolución sin justificación."""

    origen: EstadoKanban
    destino: EstadoKanban
