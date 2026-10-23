"""Pruebas unitarias para las mónadas funcionales Resultado y Opcion."""

from dataclasses import FrozenInstanceError

import pytest

from app.domain.monadas import Alguno, Exito, Fallo, Ninguno, Opcion, Resultado


class TestResultadoMonada:
    """Suite de pruebas para la mónada Resultado[T, E] y sus variantes Exito y Fallo."""

    def testExitoPropiedadesYMetodosBasicos(self) -> None:
        """Verifica el comportamiento de una instancia exitosa."""
        res: Resultado[int, str] = Exito(42)

        assert res.esExito() is True
        assert res.esFallo() is False
        assert res.obtenerValor() == 42
        assert res.obtenerO(100) == 42

        with pytest.raises(ValueError, match="No es posible extraer error"):
            res.obtenerError()

    def testFalloPropiedadesYMetodosBasicos(self) -> None:
        """Verifica el comportamiento de una instancia fallida."""
        res: Resultado[int, str] = Fallo("Error de validación")

        assert res.esExito() is False
        assert res.esFallo() is True
        assert res.obtenerError() == "Error de validación"
        assert res.obtenerO(100) == 100

        with pytest.raises(ValueError, match="No es posible extraer valor"):
            res.obtenerValor()

    def testMapeoFuncional(self) -> None:
        """Verifica las operaciones funcionales mapear y mapearFallo."""
        exito: Resultado[int, str] = Exito(10)
        exitoMapeado = exito.mapear(lambda n: n * 2)
        assert exitoMapeado == Exito(20)

        fallo: Resultado[int, str] = Fallo("error inicial")
        falloMapeado = fallo.mapear(lambda n: n * 2)
        assert falloMapeado == Fallo("error inicial")

        falloTransformado = fallo.mapearFallo(lambda e: e.upper())
        assert falloTransformado == Fallo("ERROR INICIAL")

        exitoInalterado = exito.mapearFallo(lambda e: e.upper())
        assert exitoInalterado == Exito(10)

    def testVinculacionMonadica(self) -> None:
        """Verifica el encadenamiento mónadico (vincular / flatMap)."""

        def dividir(a: int, b: int) -> Resultado[float, str]:
            if b == 0:
                return Fallo("División para cero")
            return Exito(a / b)

        resValido = Exito(20).vincular(lambda x: dividir(x, 4))
        assert resValido == Exito(5.0)

        resInvalido = Exito(20).vincular(lambda x: dividir(x, 0))
        assert resInvalido == Fallo("División para cero")

        falloPrevio: Resultado[int, str] = Fallo("Fallo anterior")
        resPropagado = falloPrevio.vincular(lambda x: dividir(x, 2))
        assert resPropagado == Fallo("Fallo anterior")

    def testInmutabilidadEstricta(self) -> None:
        """Comprueba que la modificación de atributos lance FrozenInstanceError."""
        exito = Exito("Dato")
        with pytest.raises(FrozenInstanceError):
            exito.valor = "Otro dato"  # type: ignore

        fallo = Fallo("Error")
        with pytest.raises(FrozenInstanceError):
            fallo.error = "Otro error"  # type: ignore

    def testPatternMatchingEstructural(self) -> None:
        """Verifica la compatibilidad exhaustiva con match/case de Python 3.10+."""

        def clasificarResultado(res: Resultado[int, str]) -> str:
            match res:
                case Exito(v):
                    return f"Valor: {v}"
                case Fallo(e):
                    return f"Error: {e}"

        assert clasificarResultado(Exito(100)) == "Valor: 100"
        assert clasificarResultado(Fallo("Invalido")) == "Error: Invalido"


class TestOpcionMonada:
    """Suite de pruebas para la mónada Opcion[T] y sus variantes Alguno y Ninguno."""

    def testAlgunoPropiedadesYMetodos(self) -> None:
        """Verifica el comportamiento de una instancia presente."""
        opcion: Opcion[str] = Alguno("AgilBan")

        assert opcion.esAlguno() is True
        assert opcion.esNinguno() is False
        assert opcion.obtenerValor() == "AgilBan"
        assert opcion.obtenerO("Por defecto") == "AgilBan"
        assert opcion.aOpcional() == "AgilBan"

    def testNingunoPropiedadesYMetodos(self) -> None:
        """Verifica el comportamiento de la ausencia controlada de valor."""
        opcion: Opcion[str] = Ninguno()

        assert opcion.esAlguno() is False
        assert opcion.esNinguno() is True
        assert opcion.obtenerO("Por defecto") == "Por defecto"
        assert opcion.aOpcional() is None

        with pytest.raises(ValueError, match="No es posible extraer valor"):
            opcion.obtenerValor()

    def testDesdeOpcionalFabrica(self) -> None:
        """Verifica la construcción mediante la factoría desdeOpcional."""
        assert Opcion.desdeOpcional("Hola") == Alguno("Hola")
        assert Opcion.desdeOpcional(None) == Ninguno()

    def testMapeoYVinculacionOpcion(self) -> None:
        """Verifica mapear y vincular sobre Opcion."""
        alguno: Opcion[int] = Alguno(5)
        assert alguno.mapear(lambda n: n * 10) == Alguno(50)
        assert alguno.vincular(lambda n: Alguno(str(n))) == Alguno("5")
        assert alguno.vincular(lambda _: Ninguno()) == Ninguno()

        ninguno: Opcion[int] = Ninguno()
        assert ninguno.mapear(lambda n: n * 10) == Ninguno()
        assert ninguno.vincular(lambda n: Alguno(str(n))) == Ninguno()

    def testInmutabilidadOpcion(self) -> None:
        """Verifica inmutabilidad estricta en Alguno y Ninguno."""
        alguno = Alguno("Inmutable")
        with pytest.raises(FrozenInstanceError):
            alguno.valor = "Mutado"  # type: ignore

    def testPatternMatchingOpcion(self) -> None:
        """Verifica el desempaquetado con match/case para Opcion."""

        def clasificarOpcion(opc: Opcion[str]) -> str:
            match opc:
                case Alguno(v):
                    return f"Contiene: {v}"
                case Ninguno():
                    return "Vacio"

        assert clasificarOpcion(Alguno("Python")) == "Contiene: Python"
        assert clasificarOpcion(Ninguno()) == "Vacio"
