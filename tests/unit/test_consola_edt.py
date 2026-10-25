"""Pruebas unitarias para la interfaz de consola de EDT, Integrantes y Descarte Lógico."""

from __future__ import annotations

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
from app.ui.consolaEdt import ejecutarMenuEdt


def crearLectorSimulado(respuestas: list[str]) -> Callable[[str], str]:
    """Genera una función lectora pura que consume secuencialmente una lista de respuestas."""
    iterador = iter(respuestas)

    def lector(prompt: str) -> str:
        try:
            return next(iterador)
        except StopIteration:
            return "0"

    return lector


def configurarProyectoBase() -> tuple[sqlite3.Connection, Proyecto]:
    """Inicializa una base de datos SQLite en memoria con un proyecto preconfigurado."""
    con = sqlite3.connect(":memory:")
    inicializarEsquema(con)

    integ1 = Integrante(
        "0911111111",
        "PROY-100",
        "Carlos Bernabe",
        CargoIntegrante.DESARROLLADOR_FULLSTACK,
    )
    integ2 = Integrante(
        "0922222222",
        "PROY-100",
        "Javier Infante",
        CargoIntegrante.INGENIERO_QA,
    )
    paq1 = PaqueteTrabajo("PAQ-100", "PROY-100", "Fase Inicial", ())
    paqVacio = PaqueteTrabajo("PAQ-101", "PROY-100", "Paquete Vacio", ())
    proy = Proyecto(
        "PROY-100",
        "Proyecto de Prueba EDT",
        TipoProyecto.DESARROLLO_WEB,
        (paq1, paqVacio),
        (integ1, integ2),
    )
    guardarProyectoCompleto(con, proy)
    return con, proy


def testAgregarNuevoPaqueteExito() -> None:
    """Verifica que un paquete nuevo con nombre válido sea persistido en la EDT."""
    con, proy = configurarProyectoBase()
    entradas = [
        "3",  # Opción: Agregar nuevo paquete
        "Despliegue e Infraestructura",  # Nombre válido
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuEdt(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any("agregado exitosamente" in m.lower() for m in mensajes)

    res = recuperarProyectos(con)
    assert isinstance(res, Exito)
    pRecup = res.valor[0]
    nombresPaquetes = [p.nombre for p in pRecup.paquetes]
    assert "Despliegue e Infraestructura" in nombresPaquetes


def testRenombrarPaqueteExito() -> None:
    """Verifica el renombrado exitoso de un paquete de trabajo."""
    con, proy = configurarProyectoBase()
    entradas = [
        "4",  # Opción: Renombrar paquete
        "1",  # Seleccionar paquete 1 ('Fase Inicial')
        "Fase de Inicio y Alcance",  # Nuevo nombre
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuEdt(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any("renombrado exitosamente" in m.lower() for m in mensajes)

    res = recuperarProyectos(con)
    assert isinstance(res, Exito)
    nombres = [p.nombre for p in res.valor[0].paquetes]
    assert "Fase de Inicio y Alcance" in nombres


def testEliminarPaqueteVacioYBloqueoConTareas() -> None:
    """Verifica que un paquete con tareas bloquee la eliminación y uno vacío sea eliminado."""
    con, proy = configurarProyectoBase()

    # Asignar una tarea al paquete 1 (PAQ-100)
    hist = TransicionHistorial(
        "TR-1",
        "TAR-100",
        EstadoKanban.PENDIENTE,
        EstadoKanban.PENDIENTE,
        "2026-10-25T18:00:00",
        Ninguno(),
    )
    tarea = Tarea(
        "TAR-100",
        "PAQ-100",
        "Tarea de Prueba",
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

    # 1. Intentar eliminar paquete con tareas (bloqueo)
    entradasBloqueo = [
        "5",  # Opción eliminar paquete
        "1",  # Paquete 1 (PAQ-100 con tareas)
        "0",  # Salir
    ]
    mensajes: list[str] = []
    ejecutarMenuEdt(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradasBloqueo),
        emisor=mensajes.append,
    )
    assert any(
        "bloqueada" in m.lower() or "contiene tareas" in m.lower() for m in mensajes
    )

    # 2. Eliminar paquete 2 vacío (PAQ-101)
    entradasEliminar = [
        "5",  # Opción eliminar paquete
        "2",  # Paquete 2 vacío
        "S",  # Confirmación
        "0",  # Salir
    ]
    mensajes.clear()
    ejecutarMenuEdt(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradasEliminar),
        emisor=mensajes.append,
    )
    assert any("eliminado exitosamente" in m.lower() for m in mensajes)

    res = recuperarProyectos(con)
    assert isinstance(res, Exito)
    ids = [p.idPaquete for p in res.valor[0].paquetes]
    assert "PAQ-101" not in ids


def testAgregarNuevoIntegranteExito() -> None:
    """Verifica la validación e incorporación de un nuevo integrante al proyecto."""
    con, proy = configurarProyectoBase()
    entradas = [
        "6",  # Opción agregar integrante
        "0933333333",  # Cédula válida
        "Deivy Prudente",  # Nombre válido
        "2",  # Cargo: Desarrollador Backend
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuEdt(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any("incorporado exitosamente" in m.lower() for m in mensajes)

    res = recuperarProyectos(con)
    assert isinstance(res, Exito)
    cedulas = [i.cedula for i in res.valor[0].integrantes]
    assert "0933333333" in cedulas


def testEliminarIntegranteBloqueoYExito() -> None:
    """Verifica el bloqueo de eliminación si tiene tareas activas y el éxito cuando no las tiene."""
    con, proy = configurarProyectoBase()

    # Asignar tarea activa al integrante 1 (0911111111 - Carlos Bernabe)
    hist = TransicionHistorial(
        "TR-1",
        "TAR-101",
        EstadoKanban.PENDIENTE,
        EstadoKanban.PENDIENTE,
        "2026-10-25T18:00:00",
        Ninguno(),
    )
    tarea = Tarea(
        "TAR-101",
        "PAQ-100",
        "Diseño Arquitectónico",
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

    # 1. Intentar eliminar a Carlos Bernabe (bloqueado por tarea activa)
    entradasBloqueo = [
        "7",  # Opción eliminar integrante
        "1",  # Carlos Bernabe
        "0",  # Salir
    ]
    mensajes: list[str] = []
    ejecutarMenuEdt(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradasBloqueo),
        emisor=mensajes.append,
    )
    assert any(
        "bloqueada" in m.lower() or "tareas activas" in m.lower() for m in mensajes
    )

    # 2. Eliminar a Javier Infante (no tiene tareas asignadas)
    entradasExito = [
        "7",  # Opción eliminar integrante
        "2",  # Javier Infante
        "S",  # Confirmación
        "0",  # Salir
    ]
    mensajes.clear()
    ejecutarMenuEdt(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradasExito),
        emisor=mensajes.append,
    )
    assert any("desvinculado exitosamente" in m.lower() for m in mensajes)

    res = recuperarProyectos(con)
    assert isinstance(res, Exito)
    cedulas = [i.cedula for i in res.valor[0].integrantes]
    assert "0922222222" not in cedulas


def testDescarteLogicoTareaEnEdt() -> None:
    """Verifica que el descarte lógico asigne activo=False preservando el registro en SQLite."""
    con, proy = configurarProyectoBase()

    hist = TransicionHistorial(
        "TR-1",
        "TAR-200",
        EstadoKanban.PENDIENTE,
        EstadoKanban.PENDIENTE,
        "2026-10-25T18:00:00",
        Ninguno(),
    )
    tarea = Tarea(
        "TAR-200",
        "PAQ-100",
        "Tarea Para Descartar",
        Ninguno(),
        PrioridadTarea.BAJA,
        Ninguno(),
        Ninguno(),
        EstadoKanban.PENDIENTE,
        0,
        True,
        (hist,),
    )
    guardarTareaConHistorial(con, tarea)

    entradas = [
        "8",  # Descartar tarea lógicamente
        "1",  # Seleccionar Paquete 1
        "1",  # Seleccionar Tarea 1 (TAR-200)
        "S",  # Confirmar descarte
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuEdt(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any("descartada lógicamente" in m.lower() for m in mensajes)

    # Verificar en base de datos que activo = False
    cursor = con.cursor()
    cursor.execute("SELECT activo FROM tareas WHERE id_tarea = 'TAR-200'")
    fila = cursor.fetchone()
    assert fila is not None
    assert fila[0] == 0  # Activo = 0 (False)


def testMenuEdtNavegacionTablas() -> None:
    """Verifica que las opciones de visualización de EDT y Equipo emitan los reportes."""
    con, proy = configurarProyectoBase()
    entradas = [
        "1",  # Ver EDT
        "2",  # Ver Integrantes
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuEdt(
        con,
        proy.idProyecto,
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert any("EDT (ESTRUCTURA DE DESGLOSE DEL TRABAJO)" in m for m in mensajes)
    assert any("CÉDULA" in m and "CARGO" in m for m in mensajes)
