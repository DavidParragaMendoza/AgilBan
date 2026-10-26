"""Módulo del núcleo funcional puro (EDT, Kanban, métricas y filtros)."""

from app.core.edt import (
    agregarPaqueteAProyecto,
    calcularAvancePaquete,
    calcularEstadoPaquete,
    obtenerTareasActivas,
    renombrarPaquete,
)
from app.core.filtros import (
    crearCriterioFiltro,
    filtrarTareas,
    ordenarPorFecha,
    ordenarPorPrioridad,
)
from app.core.kanban import (
    avanzarOTareasKanban,
    descartarTareaLogicamente,
    destinoRetroceso,
    editarTarea,
    esRetroceso,
    transicionesPermitidas,
)
from app.core.metricas import (
    auditarCuellosDeBotella,
    calcularAvanceGlobal,
    calcularCargaIntegrantes,
    calcularResumenTareas,
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
    "auditarCuellosDeBotella",
    "avanzarOTareasKanban",
    "calcularAvanceGlobal",
    "calcularAvancePaquete",
    "calcularCargaIntegrantes",
    "calcularEstadoPaquete",
    "calcularResumenTareas",
    "crearCriterioFiltro",
    "descartarTareaLogicamente",
    "destinoRetroceso",
    "editarTarea",
    "esRetroceso",
    "filtrarTareas",
    "obtenerTareasActivas",
    "ordenarPorFecha",
    "ordenarPorPrioridad",
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
