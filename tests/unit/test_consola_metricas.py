"""Pruebas unitarias para la interfaz de consola de Métricas, Cuellos de Botella y Filtros."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from app.adapters.esquemaSqlite import inicializarEsquema
from app.adapters.repositorioSqlite import (
    guardarProyectoCompleto,
    guardarTareaConHistorial,
)
from app.domain.catalogos import (
    CargoIntegrante,
    EstadoKanban,
    PrioridadTarea,
    TipoProyecto,
)
from app.domain.modelos import (
    Integrante,
    PaqueteTrabajo,
    Proyecto,
    Tarea,
    TransicionHistorial,
)
from app.domain.monadas import Alguno, Ninguno
from app.ui.consolaMetricas import ejecutarMenuMetricas


def crearLectorSimulado(respuestas: list[str]) -> Callable[[str], str]:
    """Genera una función lectora pura que consume respuestas de una lista predefinida."""
    iterador = iter(respuestas)

    def lector(prompt: str) -> str:
        try:
            return next(iterador)
        except StopIteration:
            return "0"

    return lector


def configurarProyectoAnalitico() -> tuple[sqlite3.Connection, Proyecto]:
    """Inicializa una base de datos SQLite en memoria con un proyecto con múltiples tareas e historial."""
    con = sqlite3.connect(":memory:")
    inicializarEsquema(con)

    integ = Integrante(
        "0944444444",
        "PROY-300",
        "Javier Infante",
        CargoIntegrante.INGENIERO_QA,
    )
    paq = PaqueteTrabajo("PAQ-300", "PROY-300", "Sprint QA", ())
    proy = Proyecto(
        "PROY-300",
        "Sistema de Pruebas Analíticas",
        TipoProyecto.CIENCIA_DATOS_IA,
        (paq,),
        (integ,),
    )
    guardarProyectoCompleto(con, proy)

    # Tarea 1: Terminada, con 2 regresos y justificaciones
    trans1 = TransicionHistorial(
        "TR-1",
        "TAR-301",
        EstadoKanban.PENDIENTE,
        EstadoKanban.EN_PROGRESO,
        "2026-10-20T10:00:00",
        Ninguno(),
    )
    trans2 = TransicionHistorial(
        "TR-2",
        "TAR-301",
        EstadoKanban.EN_PROGRESO,
        EstadoKanban.PENDIENTE,
        "2026-10-21T11:00:00",
        Alguno("Error de configuración de entorno"),
    )
    trans3 = TransicionHistorial(
        "TR-3",
        "TAR-301",
        EstadoKanban.EN_REVISION,
        EstadoKanban.EN_PROGRESO,
        "2026-10-22T12:00:00",
        Alguno("Fallo en prueba de regresión"),
    )
    t1 = Tarea(
        idTarea="TAR-301",
        idPaquete="PAQ-300",
        titulo="Modelado Predictivo",
        descripcion=Alguno("Algoritmo de clustering"),
        prioridad=PrioridadTarea.CRITICA,
        cedulaResponsable=Alguno("0944444444"),
        fechaObjetivo=Alguno("2026-10-22"),
        estado=EstadoKanban.TERMINADA,
        contadorRegresos=2,
        activo=True,
        historial=(trans1, trans2, trans3),
    )
    guardarTareaConHistorial(con, t1)

    # Tarea 2: En progreso, sin regresos
    t2 = Tarea(
        idTarea="TAR-302",
        idPaquete="PAQ-300",
        titulo="Limpieza de Datos",
        descripcion=Ninguno(),
        prioridad=PrioridadTarea.ALTA,
        cedulaResponsable=Alguno("0944444444"),
        fechaObjetivo=Alguno("2026-11-10"),
        estado=EstadoKanban.EN_PROGRESO,
        contadorRegresos=0,
        activo=True,
        historial=(),
    )
    guardarTareaConHistorial(con, t2)

    # Tarea 3: Inactiva (descartada)
    t3 = Tarea(
        idTarea="TAR-303",
        idPaquete="PAQ-300",
        titulo="Tarea Obsoleta",
        descripcion=Ninguno(),
        prioridad=PrioridadTarea.BAJA,
        cedulaResponsable=Ninguno(),
        fechaObjetivo=Ninguno(),
        estado=EstadoKanban.PENDIENTE,
        contadorRegresos=0,
        activo=False,
        historial=(),
    )
    guardarTareaConHistorial(con, t3)

    return con, proy


def testMostrarPanelGeneralMetricas() -> None:
    """Verifica que el panel muestre el resumen general, avance del proyecto y de la EDT."""
    con, proy = configurarProyectoAnalitico()
    entradas = [
        "1",  # Ver panel consolidado
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuMetricas(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any("PANEL DE MÉTRICAS" in m for m in mensajes)
    assert any("Tareas Activas:" in m for m in mensajes)
    assert any("Avance Global:" in m for m in mensajes)
    assert any("AVANCE DETALLADO POR PAQUETE" in m for m in mensajes)
    assert any("Sprint QA" in m for m in mensajes)


def testAuditoriaCuellosDeBotellaConRegresos() -> None:
    """Verifica el desglose de tareas con devoluciones e historial de motivos."""
    con, proy = configurarProyectoAnalitico()
    entradas = [
        "2",  # Auditar cuellos de botella
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuMetricas(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any("AUDITORÍA DE CUELLOS DE BOTELLA" in m for m in mensajes)
    assert any("Modelado Predictivo" in m for m in mensajes)
    assert any(
        "Regresos acumulados: 2" in m or "devoluciones acumuladas: 2" in m
        for m in mensajes
    )
    assert any("Error de configuración de entorno" in m for m in mensajes)
    assert any("Fallo en prueba de regresión" in m for m in mensajes)


def testFiltrarPorEstadoKanban() -> None:
    """Verifica el filtrado interactivo seleccionando EstadoKanban.TERMINADA."""
    con, proy = configurarProyectoAnalitico()
    entradas = [
        "3",  # Consulta y filtros
        "4",  # Estado: 4. Terminada
        "0",  # Todos los responsables
        "0",  # Todas las prioridades
        "N",  # Solo vencidas: No
        "N",  # Solo inactivas: No
        "0",  # Sin ordenamiento
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuMetricas(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any("Modelado Predictivo" in m for m in mensajes)
    assert not any("Limpieza de Datos" in m for m in mensajes)


def testFiltrarPorTareasInactivas() -> None:
    """Verifica el filtrado para recuperar tareas descartadas (activo = False)."""
    con, proy = configurarProyectoAnalitico()
    entradas = [
        "3",  # Consulta y filtros
        "0",  # Estado: Todos
        "0",  # Responsable: Todos
        "0",  # Prioridad: Todas
        "N",  # Solo vencidas: No
        "S",  # Solo inactivas: Sí
        "0",  # Sin ordenamiento
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuMetricas(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any("Tarea Obsoleta" in m for m in mensajes)
    assert not any("Modelado Predictivo" in m for m in mensajes)


def testFiltradoSinResultadosMensajeAmigable() -> None:
    """Verifica que cuando un filtro no encuentre coincidencias, presente un aviso claro."""
    con, proy = configurarProyectoAnalitico()
    entradas = [
        "3",  # Consulta y filtros
        "1",  # Estado: Pendiente (no hay activas pendientes en el test)
        "0",  # Todos los responsables
        "0",  # Todas las prioridades
        "N",  # Vencidas: No
        "N",  # Inactivas: No
        "0",  # Sin orden
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuMetricas(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any("no se encontraron tareas" in m.lower() for m in mensajes)
