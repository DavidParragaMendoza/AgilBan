"""Módulo de telemetría y decoradores funcionales para adaptadores I/O.

Implementa el pilar 10 de programación funcional:
- Decoradores funcionales: @cronometrarOperacion encapsula la medición de tiempo y registro
  de operaciones de base de datos sin contaminar ni alterar las entidades ni reglas del dominio.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class RegistroTelemetria:
    """Registro inmutable de telemetría para una operación cronometrada."""

    nombreOperacion: str
    duracionMs: float
    exitosa: bool
    timestamp: str


_HISTORIAL_TELEMETRIA: list[RegistroTelemetria] = []


def obtenerHistorialTelemetria() -> tuple[RegistroTelemetria, ...]:
    """Retorna una copia inmutable del historial de registros de telemetría."""
    return tuple(_HISTORIAL_TELEMETRIA)


def limpiarHistorialTelemetria() -> None:
    """Limpia todos los registros del historial de telemetría en memoria."""
    _HISTORIAL_TELEMETRIA.clear()


def cronometrarOperacion(
    funcion: Callable[..., Any] | None = None,
    *,
    nombrePersonalizado: str | None = None,
    callback: Callable[[RegistroTelemetria], None] | None = None,
) -> Any:
    """Decorador funcional que mide el tiempo de ejecución en milisegundos de una operación.

    Preserva el valor de retorno íntegro y propaga cualquier excepción de la función envuelta.
    Registra la métrica en el historial en memoria y ejecuta el callback opcional.
    """

    def decorador(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def envoltura(*args: Any, **kwargs: Any) -> Any:
            nombre = nombrePersonalizado or func.__name__
            inicio = time.perf_counter()
            exitosa = True
            try:
                return func(*args, **kwargs)
            except Exception:
                exitosa = False
                raise
            finally:
                fin = time.perf_counter()
                duracionMs = round((fin - inicio) * 1000.0, 4)
                ahoraIso = datetime.now().isoformat()
                registro = RegistroTelemetria(
                    nombreOperacion=nombre,
                    duracionMs=duracionMs,
                    exitosa=exitosa,
                    timestamp=ahoraIso,
                )
                _HISTORIAL_TELEMETRIA.append(registro)
                if callback is not None:
                    callback(registro)

        return envoltura

    if funcion is not None:
        return decorador(funcion)
    return decorador
