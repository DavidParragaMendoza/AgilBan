"""Pruebas unitarias para el decorador funcional de telemetría en app/adapters/telemetria.py."""

import time

import pytest

from app.adapters.telemetria import (
    RegistroTelemetria,
    cronometrarOperacion,
    limpiarHistorialTelemetria,
    obtenerHistorialTelemetria,
)


class TestDecoradorTelemetria:
    """Suite de pruebas para el decorador funcional @cronometrarOperacion."""

    def setup_method(self) -> None:
        """Limpia el historial de telemetría antes de cada prueba unitaria."""
        limpiarHistorialTelemetria()

    def testPreservaRetornoYArgumentos(self) -> None:
        """Verifica que la función decorada conserve sus argumentos y retorno íntegro."""

        @cronometrarOperacion
        def multiplicar(a: int, b: int) -> int:
            """Multiplica dos números enteros."""
            return a * b

        resultado = multiplicar(6, 7)

        assert resultado == 42
        historial = obtenerHistorialTelemetria()
        assert len(historial) == 1
        assert historial[0].nombreOperacion == "multiplicar"
        assert historial[0].exitosa is True
        assert historial[0].duracionMs >= 0.0

    def testRegistraTiempoEnMilisegundos(self) -> None:
        """Verifica que el decorador registre la duración en milisegundos con alta precisión."""

        @cronometrarOperacion
        def operacionConPausa() -> str:
            time.sleep(0.01)  # 10 milisegundos
            return "ok"

        resultado = operacionConPausa()

        assert resultado == "ok"
        historial = obtenerHistorialTelemetria()
        assert len(historial) == 1
        # Debe registrar al menos 9.0 ms por el sleep(0.01)
        assert historial[0].duracionMs >= 9.0
        assert historial[0].exitosa is True

    def testPreservaExcepcionLanzada(self) -> None:
        """Verifica que las excepciones no se silencien y se registre exitosa = False."""

        @cronometrarOperacion
        def operacionFallida() -> None:
            raise ValueError("Fallo controlado para prueba")

        with pytest.raises(ValueError, match="Fallo controlado para prueba"):
            operacionFallida()

        historial = obtenerHistorialTelemetria()
        assert len(historial) == 1
        assert historial[0].nombreOperacion == "operacionFallida"
        assert historial[0].exitosa is False
        assert historial[0].duracionMs >= 0.0

    def testNombrePersonalizadoYCallback(self) -> None:
        """Verifica el soporte para nombre personalizado y callback de notificación."""
        capturas: list[RegistroTelemetria] = []

        def miCallback(reg: RegistroTelemetria) -> None:
            capturas.append(reg)

        @cronometrarOperacion(
            nombrePersonalizado="InsertarEnSqlite", callback=miCallback
        )
        def insertarDato(dato: str) -> str:
            return f"guardado:{dato}"

        resultado = insertarDato("tarea-1")

        assert resultado == "guardado:tarea-1"
        assert len(capturas) == 1
        assert capturas[0].nombreOperacion == "InsertarEnSqlite"
        assert capturas[0].exitosa is True

        historial = obtenerHistorialTelemetria()
        assert len(historial) == 1
        assert historial[0].nombreOperacion == "InsertarEnSqlite"

    def testPreservaMetadatosFuncion(self) -> None:
        """Verifica que functools.wraps preserve el nombre y docstring de la función envuelta."""

        @cronometrarOperacion
        def consultaSql() -> str:
            """Ejecuta una consulta SQL en base de datos."""
            return "filas"

        assert consultaSql.__name__ == "consultaSql"
        assert consultaSql.__doc__ == "Ejecuta una consulta SQL en base de datos."

    def testLimpiarHistorialTelemetria(self) -> None:
        """Verifica que limpiarHistorialTelemetria vacíe correctamente el almacén."""

        @cronometrarOperacion
        def ping() -> str:
            return "pong"

        ping()
        ping()
        assert len(obtenerHistorialTelemetria()) == 2

        limpiarHistorialTelemetria()
        assert len(obtenerHistorialTelemetria()) == 0
