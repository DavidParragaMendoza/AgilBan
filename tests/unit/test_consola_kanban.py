"""Pruebas unitarias para la interfaz de consola del Tablero Kanban (consolaKanban.py)."""

import sqlite3
from collections.abc import Callable

from app.adapters.esquemaSqlite import inicializarEsquema
from app.adapters.repositorioSqlite import (
    guardarProyectoCompleto,
    guardarTareaConHistorial,
    recuperarProyectos,
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
from app.domain.monadas import Alguno, Exito, Ninguno
from app.ui.consolaKanban import ejecutarMenuKanban


def crearLectorSimulado(respuestas: list[str]) -> Callable[[str], str]:
    """Genera una función lectora pura que consume una lista predeterminada de respuestas."""
    iterador = iter(respuestas)

    def lector(prompt: str) -> str:
        try:
            return next(iterador)
        except StopIteration:
            return "0"

    return lector


def configurarProyectoEnMemoria() -> tuple[sqlite3.Connection, Proyecto]:
    """Inicializa base de datos SQLite y proyecto de prueba."""
    con = sqlite3.connect(":memory:")
    inicializarEsquema(con)

    integ = Integrante(
        "0911111111",
        "PROY-001",
        "Deivy Prudente",
        CargoIntegrante.DESARROLLADOR_FULLSTACK,
    )
    paq = PaqueteTrabajo("PAQ-001", "PROY-001", "Sprint 1", ())
    proy = Proyecto(
        "PROY-001", "Sistema Kanban", TipoProyecto.DESARROLLO_WEB, (paq,), (integ,)
    )
    guardarProyectoCompleto(con, proy)
    return con, proy


def testAltaRapidaTareaEnKanban() -> None:
    """Verifica que la opción de alta rápida registre una nueva tarea en el tablero y SQLite."""
    con, proy = configurarProyectoEnMemoria()
    entradas = [
        "1",  # Seleccionar Paquete 1 (Sprint 1)
        "2",  # Opción Alta Rápida de Tarea
        "Crear Endpoint de Login",  # Título
        "1",  # Prioridad: Baja
        "Autenticación JWT",  # Descripción
        "1",  # Responsable: Deivy Prudente
        "2026-11-15",  # Fecha objetivo
        "0",  # Volver del tablero del paquete
        "0",  # Salir de selección de paquetes
    ]
    mensajes: list[str] = []

    ejecutarMenuKanban(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any("guardada exitosamente" in m.lower() for m in mensajes)

    # Verificar persistencia en base de datos
    res = recuperarProyectos(con)
    assert isinstance(res, Exito)
    pRecup = res.valor[0]
    tareas = pRecup.paquetes[0].tareas
    assert len(tareas) == 1
    assert tareas[0].titulo == "Crear Endpoint de Login"
    assert tareas[0].estado == EstadoKanban.PENDIENTE
    assert tareas[0].contadorRegresos == 0


def testTransicionAvanceSinJustificacion() -> None:
    """Verifica que un avance Kanban no requiera justificación y actualice el estado a En progreso."""
    con, proy = configurarProyectoEnMemoria()
    hist = TransicionHistorial(
        "TR-0",
        "TAR-001",
        EstadoKanban.PENDIENTE,
        EstadoKanban.PENDIENTE,
        "2026-10-25T17:00:00",
        Ninguno(),
    )
    tarea = Tarea(
        "TAR-001",
        "PAQ-001",
        "Diseñar Modelo ER",
        Ninguno(),
        PrioridadTarea.MEDIA,
        Alguno("0911111111"),
        Ninguno(),
        EstadoKanban.PENDIENTE,
        0,
        True,
        (hist,),
    )
    guardarTareaConHistorial(con, tarea)

    entradas = [
        "1",  # Seleccionar Paquete 1
        "1",  # Mover / Transicionar estado
        "1",  # Seleccionar TAR-001
        "1",  # Opción 1: Mover a 'En progreso' (Avance)
        "0",  # Volver del paquete
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuKanban(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any("actualizada con éxito" in m.lower() for m in mensajes)

    res = recuperarProyectos(con)
    assert isinstance(res, Exito)
    t = res.valor[0].paquetes[0].tareas[0]
    assert t.estado == EstadoKanban.EN_PROGRESO
    assert t.contadorRegresos == 0


def testTransicionRetrocesoExigeJustificacion() -> None:
    """Verifica que un retroceso Kanban exija justificación obligatoria y persista el incremento de regresos."""
    con, proy = configurarProyectoEnMemoria()
    hist = TransicionHistorial(
        "TR-1",
        "TAR-001",
        EstadoKanban.PENDIENTE,
        EstadoKanban.EN_PROGRESO,
        "2026-10-25T18:00:00",
        Ninguno(),
    )
    tarea = Tarea(
        "TAR-001",
        "PAQ-001",
        "Implementar Auth",
        Ninguno(),
        PrioridadTarea.ALTA,
        Alguno("0911111111"),
        Ninguno(),
        EstadoKanban.EN_PROGRESO,
        0,
        True,
        (hist,),
    )
    guardarTareaConHistorial(con, tarea)

    entradas = [
        "1",  # Seleccionar Paquete 1
        "1",  # Mover / Transicionar estado
        "1",  # Seleccionar TAR-001
        "2",  # Opción de retroceso hacia Pendiente
        "",  # Justificación vacía -> Error
        "Faltan pruebas unitarias de seguridad",  # Justificación válida
        "0",  # Volver del paquete
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuKanban(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any(
        "obligatorio" in m.lower() or "justificación" in m.lower() for m in mensajes
    )
    assert any("actualizada con éxito" in m.lower() for m in mensajes)

    # Verificar que el contador de regresos aumentó a 1
    res = recuperarProyectos(con)
    assert isinstance(res, Exito)
    t = res.valor[0].paquetes[0].tareas[0]
    assert t.estado == EstadoKanban.PENDIENTE
    assert t.contadorRegresos == 1
    assert any(
        "Faltan pruebas unitarias" in h.comentario.valor
        for h in t.historial
        if isinstance(h.comentario, Alguno)
    )


def testVerDetalleTareaEHistorial() -> None:
    """Verifica que la opción 3 muestre el detalle y trazabilidad histórica de la tarea."""
    con, proy = configurarProyectoEnMemoria()
    hist = TransicionHistorial(
        "TR-1",
        "TAR-001",
        EstadoKanban.PENDIENTE,
        EstadoKanban.EN_PROGRESO,
        "2026-10-25T18:00:00",
        Ninguno(),
    )
    tarea = Tarea(
        "TAR-001",
        "PAQ-001",
        "Tarea Detallada",
        Alguno("Documentación técnica"),
        PrioridadTarea.CRITICA,
        Alguno("0911111111"),
        Ninguno(),
        EstadoKanban.EN_PROGRESO,
        0,
        True,
        (hist,),
    )
    guardarTareaConHistorial(con, tarea)

    entradas = [
        "1",  # Seleccionar Paquete 1
        "3",  # Ver detalle
        "1",  # Seleccionar tarea 1
        "0",  # Volver
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuKanban(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any("detalle de la tarea" in m.lower() for m in mensajes)
    assert any("Documentación técnica" in m for m in mensajes)
    assert any("Crítica" in m for m in mensajes)


def testMenuKanbanProyectoSinPaquetes() -> None:
    """Verifica que el menú Kanban maneje correctamente proyectos sin paquetes de trabajo."""
    con = sqlite3.connect(":memory:")
    inicializarEsquema(con)
    proy = Proyecto("PROY-002", "Proyecto Vacío", TipoProyecto.APLICACION_MOVIL, (), ())
    guardarProyectoCompleto(con, proy)

    mensajes: list[str] = []
    ejecutarMenuKanban(
        con, proy.idProyecto, lector=lambda _: "0", emisor=mensajes.append
    )

    assert any("no tiene paquetes de trabajo" in m.lower() for m in mensajes)
