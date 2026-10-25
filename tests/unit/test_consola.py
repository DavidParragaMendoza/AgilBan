"""Pruebas unitarias para el menú principal y bucle REPL de navegación (consola.py)."""

import sqlite3
from collections.abc import Callable

from app.adapters.esquemaSqlite import inicializarEsquema
from app.adapters.repositorioSqlite import guardarProyectoCompleto
from app.domain.catalogos import CargoIntegrante, TipoProyecto
from app.domain.modelos import Integrante, PaqueteTrabajo, Proyecto
from app.ui.consola import ejecutarMenuPrincipal


def crearLectorSimulado(respuestas: list[str]) -> Callable[[str], str]:
    """Genera una función lectora pura que consume una lista predeterminada de respuestas."""
    iterador = iter(respuestas)

    def lector(prompt: str) -> str:
        try:
            return next(iterador)
        except StopIteration:
            return "0"

    return lector


def conexionEnMemoria() -> sqlite3.Connection:
    """Crea una base de datos SQLite en memoria con el esquema inicializado."""
    con = sqlite3.connect(":memory:")
    inicializarEsquema(con)
    return con


def testMenuPrincipalBienvenidaYSalir() -> None:
    """Verifica que el menú emita mensaje de bienvenida cuando no hay proyectos y permita salir limpiamente."""
    con = conexionEnMemoria()
    entradas = [
        "1",  # Listar proyectos (vacío)
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuPrincipal(
        con, lector=crearLectorSimulado(entradas), emisor=mensajes.append
    )

    assert any("No hay proyectos registrados" in m for m in mensajes)
    assert any("Saliendo de AgilBan" in m or "Hasta luego" in m for m in mensajes)


def testMenuPrincipalManejaOpcionesInvalidas() -> None:
    """Verifica que ante entradas no numéricas o fuera de rango emita advertencia sin colapsar."""
    con = conexionEnMemoria()
    entradas = [
        "letras_invalidas",
        "99",  # Fuera de rango
        "0",  # Salir
    ]
    mensajes: list[str] = []

    ejecutarMenuPrincipal(
        con, lector=crearLectorSimulado(entradas), emisor=mensajes.append
    )

    assert any("Opción no reconocida" in m or "válido" in m.lower() for m in mensajes)


def testMenuPrincipalSeleccionarProyectoYVolver() -> None:
    """Verifica la navegación hacia el menú de proyecto activo y el retorno al menú principal."""
    con = conexionEnMemoria()
    integ = Integrante(
        "0912345678", "PROY-001", "Ana Lopez", CargoIntegrante.LIDER_PROYECTO
    )
    paq = PaqueteTrabajo("PAQ-001", "PROY-001", "Fase 1", ())
    proy = Proyecto(
        "PROY-001", "Portal Web", TipoProyecto.DESARROLLO_WEB, (paq,), (integ,)
    )
    guardarProyectoCompleto(con, proy)

    entradas = [
        "2",  # Seleccionar proyecto
        "1",  # Seleccionar el primer proyecto
        "0",  # Volver al menú principal desde el proyecto
        "0",  # Salir del sistema
    ]
    mensajes: list[str] = []

    ejecutarMenuPrincipal(
        con, lector=crearLectorSimulado(entradas), emisor=mensajes.append
    )

    assert any("Portal Web" in m for m in mensajes)
    assert any("PROYECTO ACTIVO" in m for m in mensajes)
