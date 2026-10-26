"""Pruebas unitarias para el punto de entrada y ciclo de arranque de la aplicación."""

from __future__ import annotations

from unittest.mock import patch

from app.consola import iniciarAplicacion, main
from app.domain.monadas import Fallo


def testIniciarAplicacionExitoYSalidaLimpia() -> None:
    """Verifica que iniciarAplicacion arranque con éxito en base de datos en memoria y cierre en opción 0."""
    mensajes: list[str] = []
    codigoSalida = iniciarAplicacion(
        rutaBaseDatos=":memory:",
        lector=lambda _: "0",
        emisor=mensajes.append,
    )

    assert codigoSalida == 0
    assert any("BIENVENIDO A AGILBAN" in m for m in mensajes)
    assert any("MENÚ PRINCIPAL AGILBAN" in m for m in mensajes)
    assert any("Saliendo de AgilBan" in m for m in mensajes)


def testIniciarAplicacionInterrupcionTeclado() -> None:
    """Verifica el manejo resiliente y limpio ante una interrupción de teclado (Ctrl+C)."""
    mensajes: list[str] = []

    def lectorInterrumpido(prompt: str) -> str:
        raise KeyboardInterrupt()

    codigoSalida = iniciarAplicacion(
        rutaBaseDatos=":memory:",
        lector=lectorInterrumpido,
        emisor=mensajes.append,
    )

    assert codigoSalida == 0
    assert any("Sesión interrumpida por el usuario" in m for m in mensajes)


def testIniciarAplicacionFalloEsquema() -> None:
    """Verifica que un error al inicializar el esquema reporte fallo y código de salida 1."""
    mensajes: list[str] = []

    with patch(
        "app.consola.inicializarEsquema",
        return_value=Fallo("Fallo simulado de DDL"),
    ):
        codigoSalida = iniciarAplicacion(
            rutaBaseDatos=":memory:",
            lector=lambda _: "0",
            emisor=mensajes.append,
        )

    assert codigoSalida == 1
    assert any("Error al inicializar el esquema" in m for m in mensajes)


def testMainEjecutaSysExit() -> None:
    """Verifica que la función main invoque sys.exit pasando el código de salida de iniciarAplicacion."""
    with (
        patch("app.consola.iniciarAplicacion", return_value=0) as mockIniciar,
        patch("sys.exit") as mockExit,
    ):
        main()
        mockIniciar.assert_called_once()
        mockExit.assert_called_once_with(0)
