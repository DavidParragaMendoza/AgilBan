"""Módulo de persistencia transaccional SQLite3 y telemetría."""

from app.adapters.esquemaSqlite import DDL_ESQUEMA, inicializarEsquema
from app.adapters.repositorioSqlite import (
    actualizarNombrePaquete,
    eliminarIntegrante,
    eliminarPaqueteVacio,
    guardarProyectoCompleto,
    guardarTareaConHistorial,
    recuperarProyectos,
)
from app.adapters.telemetria import (
    RegistroTelemetria,
    cronometrarOperacion,
    limpiarHistorialTelemetria,
    obtenerHistorialTelemetria,
)

__all__ = [
    "DDL_ESQUEMA",
    "RegistroTelemetria",
    "actualizarNombrePaquete",
    "cronometrarOperacion",
    "eliminarIntegrante",
    "eliminarPaqueteVacio",
    "guardarProyectoCompleto",
    "guardarTareaConHistorial",
    "inicializarEsquema",
    "limpiarHistorialTelemetria",
    "obtenerHistorialTelemetria",
    "recuperarProyectos",
]
