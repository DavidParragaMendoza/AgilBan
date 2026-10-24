"""Módulo del núcleo funcional puro (EDT, Kanban, métricas y filtros)."""

from app.core.edt import (
    agregarPaqueteAProyecto,
    calcularAvancePaquete,
    calcularEstadoPaquete,
    obtenerTareasActivas,
    renombrarPaquete,
)
from app.core.kanban import (
    avanzarOTareasKanban,
    descartarTareaLogicamente,
    editarTarea,
    esRetroceso,
    transicionesPermitidas,
)
from app.core.validador import (
    validarCedula,
    validarDatosTarea,
    validarEliminacionIntegrante,
    validarEliminacionPaquete,
    validarNombreIntegrante,
    validarNombrePaquete,
    validarNombreProyecto,
)

__all__ = [
    "agregarPaqueteAProyecto",
    "avanzarOTareasKanban",
    "calcularAvancePaquete",
    "calcularEstadoPaquete",
    "descartarTareaLogicamente",
    "editarTarea",
    "esRetroceso",
    "obtenerTareasActivas",
    "renombrarPaquete",
    "transicionesPermitidas",
    "validarCedula",
    "validarDatosTarea",
    "validarEliminacionIntegrante",
    "validarEliminacionPaquete",
    "validarNombreIntegrante",
    "validarNombrePaquete",
    "validarNombreProyecto",
]
