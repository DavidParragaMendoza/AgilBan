"""Módulo de contenedores funcionales mónadas (Resultado y Opcion).

Implementa los pilares 8 y 9 de programación funcional de AgilBan:
- Ausencia explícita y controlada de valor: Opcion[T] (Alguno[T] y Ninguno).
- Manejo funcional de errores y validaciones: Resultado[T, E] (Exito[T] y Fallo[E]).

Todas las estructuras son inmutables (@dataclass(frozen=True)) y compatibles
con pattern matching estructural (match/case).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")
F = TypeVar("F")


class Resultado(ABC, Generic[T, E]):
    """Clase base abstracta para la mónada Resultado[T, E]."""

    @abstractmethod
    def esExito(self) -> bool:
        """Indica si el resultado representa una operación exitosa."""

    @abstractmethod
    def esFallo(self) -> bool:
        """Indica si el resultado representa un error o fallo."""

    @abstractmethod
    def obtenerValor(self) -> T:
        """Extrae el valor contenido si es exitoso; lanza ValueError si es fallo."""

    @abstractmethod
    def obtenerError(self) -> E:
        """Extrae el error contenido si es fallo; lanza ValueError si es exitoso."""

    @abstractmethod
    def obtenerO(self, defecto: T) -> T:
        """Retorna el valor contenido si es exitoso, o el valor por defecto si es fallo."""

    @abstractmethod
    def mapear(self, transformacion: Callable[[T], U]) -> Resultado[U, E]:
        """Aplica una función transformadora pura al valor exitoso, preservando el fallo."""

    @abstractmethod
    def mapearFallo(self, transformacion: Callable[[E], F]) -> Resultado[T, F]:
        """Aplica una función transformadora pura al error si es fallo, preservando el éxito."""

    @abstractmethod
    def vincular(
        self, transformacion: Callable[[T], Resultado[U, E]]
    ) -> Resultado[U, E]:
        """Encadena operaciones monádicas que retornan otro Resultado (flatMap/bind)."""


@dataclass(frozen=True)
class Exito(Resultado[T, Any]):
    """Variante inmutable exitosa de la mónada Resultado."""

    valor: T

    def esExito(self) -> bool:
        return True

    def esFallo(self) -> bool:
        return False

    def obtenerValor(self) -> T:
        return self.valor

    def obtenerError(self) -> Any:
        raise ValueError("No es posible extraer error de una instancia de Exito.")

    def obtenerO(self, defecto: T) -> T:
        return self.valor

    def mapear(self, transformacion: Callable[[T], U]) -> Resultado[U, Any]:
        return Exito(transformacion(self.valor))

    def mapearFallo(self, transformacion: Callable[[Any], F]) -> Resultado[T, F]:
        return self

    def vincular(
        self, transformacion: Callable[[T], Resultado[U, Any]]
    ) -> Resultado[U, Any]:
        return transformacion(self.valor)


@dataclass(frozen=True)
class Fallo(Resultado[Any, E]):
    """Variante inmutable de fallo de la mónada Resultado."""

    error: E

    def esExito(self) -> bool:
        return False

    def esFallo(self) -> bool:
        return True

    def obtenerValor(self) -> Any:
        raise ValueError(
            f"No es posible extraer valor de una instancia de Fallo: {self.error}"
        )

    def obtenerError(self) -> E:
        return self.error

    def obtenerO(self, defecto: T) -> T:
        return defecto

    def mapear(self, transformacion: Callable[[Any], U]) -> Resultado[U, E]:
        return self

    def mapearFallo(self, transformacion: Callable[[E], F]) -> Resultado[Any, F]:
        return Fallo(transformacion(self.error))

    def vincular(
        self, transformacion: Callable[[Any], Resultado[U, E]]
    ) -> Resultado[U, E]:
        return self


class Opcion(ABC, Generic[T]):
    """Clase base abstracta para la mónada Opcion[T]."""

    @abstractmethod
    def esAlguno(self) -> bool:
        """Indica si la opción contiene un valor presente."""

    @abstractmethod
    def esNinguno(self) -> bool:
        """Indica si la opción representa ausencia de valor."""

    @abstractmethod
    def obtenerValor(self) -> T:
        """Extrae el valor si está presente; lanza ValueError si es Ninguno."""

    @abstractmethod
    def obtenerO(self, defecto: T) -> T:
        """Retorna el valor si está presente, o el valor por defecto si es Ninguno."""

    @abstractmethod
    def mapear(self, transformacion: Callable[[T], U]) -> Opcion[U]:
        """Aplica una función transformadora al valor si está presente."""

    @abstractmethod
    def vincular(self, transformacion: Callable[[T], Opcion[U]]) -> Opcion[U]:
        """Encadena operaciones monádicas que retornan otra Opcion (flatMap/bind)."""

    @abstractmethod
    def aOpcional(self) -> T | None:
        """Convierte la mónada en un tipo opcional nativo de Python (T o None)."""

    @classmethod
    def desdeOpcional(cls, valor: T | None) -> Opcion[T]:
        """Construye una Opcion a partir de un valor potencialmente nulo."""
        if valor is None:
            return Ninguno()
        return Alguno(valor)


@dataclass(frozen=True)
class Alguno(Opcion[T]):
    """Variante inmutable con valor presente de la mónada Opcion."""

    valor: T

    def esAlguno(self) -> bool:
        return True

    def esNinguno(self) -> bool:
        return False

    def obtenerValor(self) -> T:
        return self.valor

    def obtenerO(self, defecto: T) -> T:
        return self.valor

    def mapear(self, transformacion: Callable[[T], U]) -> Opcion[U]:
        return Alguno(transformacion(self.valor))

    def vincular(self, transformacion: Callable[[T], Opcion[U]]) -> Opcion[U]:
        return transformacion(self.valor)

    def aOpcional(self) -> T | None:
        return self.valor


@dataclass(frozen=True)
class Ninguno(Opcion[Any]):
    """Variante inmutable representativa de la ausencia controlada de valor."""

    def esAlguno(self) -> bool:
        return False

    def esNinguno(self) -> bool:
        return True

    def obtenerValor(self) -> Any:
        raise ValueError("No es posible extraer valor de una instancia de Ninguno.")

    def obtenerO(self, defecto: T) -> T:
        return defecto

    def mapear(self, transformacion: Callable[[Any], U]) -> Opcion[U]:
        return self

    def vincular(self, transformacion: Callable[[Any], Opcion[U]]) -> Opcion[U]:
        return self

    def aOpcional(self) -> Any | None:
        return None
