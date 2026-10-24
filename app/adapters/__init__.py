"""Módulo de persistencia transaccional SQLite3 y telemetría."""

from app.adapters.esquemaSqlite import DDL_ESQUEMA, inicializarEsquema
from app.adapters.telemetria import (
    RegistroTelemetria,
    cronometrarOperacion,
    limpiarHistorialTelemetria,
    obtenerHistorialTelemetria,
)

__all__ = [
    "DDL_ESQUEMA",
    "RegistroTelemetria",
    "cronometrarOperacion",
    "inicializarEsquema",
    "limpiarHistorialTelemetria",
    "obtenerHistorialTelemetria",
]
