"""Módulo de persistencia transaccional SQLite3 y telemetría."""

from app.adapters.telemetria import (
    RegistroTelemetria,
    cronometrarOperacion,
    limpiarHistorialTelemetria,
    obtenerHistorialTelemetria,
)

__all__ = [
    "RegistroTelemetria",
    "cronometrarOperacion",
    "limpiarHistorialTelemetria",
    "obtenerHistorialTelemetria",
]
