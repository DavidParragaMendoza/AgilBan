"""Pruebas unitarias para los formateadores visuales en consola de AgilBan."""

import pytest

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
from app.ui.formateadores import (
    formatearListaTareas,
    formatearPanelMetricas,
    formatearTablaEDT,
    formatearTablaIntegrantes,
    formatearTablaProyectos,
    formatearTableroKanban,
)


@pytest.fixture
def datosEjemplo() -> tuple[Proyecto, tuple[Tarea, ...]]:
    """Crea una estructura de proyecto, paquetes e integrantes para pruebas."""
    integ1 = Integrante(
        "0912345678", "PROY-001", "Ana Gomez", CargoIntegrante.LIDER_PROYECTO
    )
    integ2 = Integrante(
        "0923456789", "PROY-001", "Carlos Ruiz", CargoIntegrante.DESARROLLADOR_BACKEND
    )

    hist1 = TransicionHistorial(
        "TR-1",
        "TAR-001",
        EstadoKanban.PENDIENTE,
        EstadoKanban.PENDIENTE,
        "2026-10-20T10:00:00",
        Ninguno(),
    )
    hist2 = TransicionHistorial(
        "TR-2",
        "TAR-002",
        EstadoKanban.PENDIENTE,
        EstadoKanban.EN_PROGRESO,
        "2026-10-21T10:00:00",
        Ninguno(),
    )
    hist3 = TransicionHistorial(
        "TR-3",
        "TAR-002",
        EstadoKanban.EN_PROGRESO,
        EstadoKanban.PENDIENTE,
        "2026-10-22T10:00:00",
        Alguno("Falta documentación de requerimientos"),
    )

    t1 = Tarea(
        "TAR-001",
        "PAQ-001",
        "Diseñar Modelo",
        Alguno("Diagrama ER"),
        PrioridadTarea.ALTA,
        Alguno("0912345678"),
        Alguno("2026-10-15"),
        EstadoKanban.PENDIENTE,
        0,
        True,
        (hist1,),
    )
    t2 = Tarea(
        "TAR-002",
        "PAQ-001",
        "Crear API",
        Ninguno(),
        PrioridadTarea.CRITICA,
        Alguno("0923456789"),
        Alguno("2026-10-30"),
        EstadoKanban.PENDIENTE,
        1,
        True,
        (hist2, hist3),
    )
    t3 = Tarea(
        "TAR-003",
        "PAQ-001",
        "Probar Login",
        Ninguno(),
        PrioridadTarea.BAJA,
        Ninguno(),
        Ninguno(),
        EstadoKanban.TERMINADA,
        0,
        True,
        (),
    )
    tInactiva = Tarea(
        "TAR-004",
        "PAQ-001",
        "Tarea Descartada",
        Ninguno(),
        PrioridadTarea.MEDIA,
        Ninguno(),
        Ninguno(),
        EstadoKanban.PENDIENTE,
        0,
        False,
        (),
    )

    paq1 = PaqueteTrabajo(
        "PAQ-001", "PROY-001", "Fase Inicial", (t1, t2, t3, tInactiva)
    )
    paq2 = PaqueteTrabajo("PAQ-002", "PROY-001", "Despliegue", ())

    proy = Proyecto(
        "PROY-001",
        "Sistema Bancario",
        TipoProyecto.DESARROLLO_WEB,
        (paq1, paq2),
        (integ1, integ2),
    )
    return proy, (t1, t2, t3, tInactiva)


def testFormatearTablaProyectosVacia() -> None:
    """Verifica el mensaje amigable cuando no existen proyectos registrados."""
    texto = formatearTablaProyectos(())
    assert "No hay proyectos registrados" in texto


def testFormatearTablaProyectosConDatos(
    datosEjemplo: tuple[Proyecto, tuple[Tarea, ...]],
) -> None:
    """Verifica que la tabla de proyectos contenga columnas y datos correctos."""
    proy, _ = datosEjemplo
    texto = formatearTablaProyectos((proy,))
    assert "PROY-001" in texto
    assert "Sistema Bancario" in texto
    assert TipoProyecto.DESARROLLO_WEB.value in texto
    assert "2" in texto  # 2 paquetes y 2 integrantes


def testFormatearTablaIntegrantes(
    datosEjemplo: tuple[Proyecto, tuple[Tarea, ...]],
) -> None:
    """Verifica la renderización de la tabla de integrantes."""
    proy, _ = datosEjemplo
    texto = formatearTablaIntegrantes(proy.integrantes)
    assert "0912345678" in texto
    assert "Ana Gomez" in texto
    assert CargoIntegrante.LIDER_PROYECTO.value in texto
    assert "0923456789" in texto
    assert "Carlos Ruiz" in texto


def testFormatearTablaEDT(datosEjemplo: tuple[Proyecto, tuple[Tarea, ...]]) -> None:
    """Verifica que la tabla EDT muestre paquetes con su avance y sus tareas."""
    proy, _ = datosEjemplo
    texto = formatearTablaEDT(proy, fechaReferencia="2026-10-25")
    assert "PAQ-001" in texto
    assert "Fase Inicial" in texto
    assert "TAR-001" in texto
    assert "TAR-002" in texto
    assert "TAR-003" in texto
    assert "TAR-004" not in texto  # No lista inactivas en vista EDT activa
    assert "PAQ-002" in texto
    assert "Sin Tareas" in texto or "0.0%" in texto
    # Tarea TAR-001 vence el 2026-10-15 y la referencia es 2026-10-25 => Vencida
    assert "Vencida" in texto


def testFormatearTableroKanban(
    datosEjemplo: tuple[Proyecto, tuple[Tarea, ...]],
) -> None:
    """Verifica que el tablero Kanban muestre las 4 columnas y datos de tarjetas."""
    proy, tareas = datosEjemplo
    tareasActivas = tuple(t for t in tareas if t.activo)
    texto = formatearTableroKanban(
        tareasActivas, proy.integrantes, fechaReferencia="2026-10-25"
    )
    assert "Pendiente" in texto
    assert "En progreso" in texto
    assert "En revisión" in texto
    assert "Terminada" in texto
    assert "TAR-001" in texto
    assert "TAR-002" in texto
    # Regresos de TAR-002
    assert "Regresos: 1" in texto or "regreso" in texto.lower()
    # Vencida para TAR-001
    assert "Vencida" in texto


def testFormatearPanelMetricas(
    datosEjemplo: tuple[Proyecto, tuple[Tarea, ...]],
) -> None:
    """Verifica que el panel de métricas incluya avance, cargas y auditoría de cuellos."""
    proy, tareas = datosEjemplo
    resumen = {
        "activas": 3,
        "inactivas": 1,
        "Pendiente": 2,
        "En progreso": 0,
        "En revisión": 0,
        "Terminada": 1,
    }
    avanceGlobal = 33.33
    carga = {
        "0912345678": {"asignadas": 1, "terminadas": 0},
        "0923456789": {"asignadas": 1, "terminadas": 0},
    }
    cuellos = (tareas[1],)  # TAR-002 tiene 1 regreso

    texto = formatearPanelMetricas(
        resumen, avanceGlobal, carga, cuellos, proy.integrantes
    )
    assert "33.33%" in texto or "33.3%" in texto
    assert "Activas: 3" in texto or "3" in texto
    assert "Inactivas: 1" in texto or "1" in texto
    assert "Ana Gomez" in texto or "0912345678" in texto
    assert "TAR-002" in texto
    assert "Falta documentación" in texto


def testFormatearListaTareasVacia() -> None:
    """Verifica mensaje de búsqueda sin resultados en filtros."""
    texto = formatearListaTareas(())
    assert (
        "No se encontraron tareas que coincidan con los criterios de filtro seleccionados."
        in texto
    )
