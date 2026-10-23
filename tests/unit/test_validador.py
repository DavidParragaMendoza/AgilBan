"""Pruebas unitarias para validaciones puras del núcleo funcional (Proyectos e Integrantes)."""

from app.core.validador import (
    validarCedula,
    validarEliminacionIntegrante,
    validarNombreIntegrante,
    validarNombreProyecto,
)
from app.domain.catalogos import CargoIntegrante
from app.domain.errores import ErrorDuplicado, ErrorReglaNegocio, ErrorValidacion
from app.domain.modelos import Integrante, Tarea
from app.domain.monadas import Alguno, Exito, Fallo


class TestValidacionProyecto:
    """Suite de pruebas para validación de nombres de proyectos."""

    def testValidarNombreProyectoValido(self) -> None:
        """UT-VAL-01: Valida un nombre de proyecto correcto no existente."""
        resultado = validarNombreProyecto("Sistema ERP", ("Portal Web", "App Móvil"))
        assert resultado == Exito("Sistema ERP")

    def testValidarNombreProyectoDuplicadoExacto(self) -> None:
        """UT-VAL-02: Rechaza nombres de proyecto ya existentes."""
        resultado = validarNombreProyecto("Portal Web", ("Portal Web", "App Móvil"))
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorDuplicado)
        assert error.entidad == "Proyecto"

    def testValidarNombreProyectoDuplicadoCaseInsensitive(self) -> None:
        """Rechaza duplicados ignorando mayúsculas y minúsculas."""
        resultado = validarNombreProyecto("portal web", ("Portal Web",))
        assert isinstance(resultado, Fallo)
        assert isinstance(resultado.obtenerError(), ErrorDuplicado)

    def testValidarNombreProyectoVacio(self) -> None:
        """Rechaza nombres vacíos o formados únicamente por espacios."""
        resultado = validarNombreProyecto("   ", ())
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorValidacion)
        assert error.campo == "nombre"

    def testValidarNombreProyectoExcedeLongitud(self) -> None:
        """Rechaza nombres de proyecto que superen los 100 caracteres."""
        nombreLargo = "A" * 101
        resultado = validarNombreProyecto(nombreLargo, ())
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorValidacion)
        assert error.campo == "nombre"


class TestValidacionIntegrante:
    """Suite de pruebas para validación y eliminación de integrantes."""

    def testValidarCedulaValida(self) -> None:
        """UT-VAL-03: Acepta cédula con exactamente 10 dígitos numéricos."""
        resultado = validarCedula("0912345678", ())
        assert resultado == Exito("0912345678")

    def testValidarCedulaLongitudInvalida(self) -> None:
        """UT-VAL-04: Rechaza cédula si no tiene exactamente 10 dígitos."""
        resultadoMenor = validarCedula("12345", ())
        assert isinstance(resultadoMenor, Fallo)
        assert isinstance(resultadoMenor.obtenerError(), ErrorValidacion)

        resultadoMayor = validarCedula("012345678901", ())
        assert isinstance(resultadoMayor, Fallo)
        assert isinstance(resultadoMayor.obtenerError(), ErrorValidacion)

    def testValidarCedulaConLetras(self) -> None:
        """Rechaza cédula si contiene caracteres no numéricos."""
        resultado = validarCedula("091234567A", ())
        assert isinstance(resultado, Fallo)
        assert isinstance(resultado.obtenerError(), ErrorValidacion)

    def testValidarCedulaDuplicadaEnProyecto(self) -> None:
        """Rechaza cédula si ya se encuentra asignada en el proyecto."""
        resultado = validarCedula("0912345678", ("0912345678", "0987654321"))
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorDuplicado)
        assert error.entidad == "Integrante"

    def testValidarNombreIntegranteValido(self) -> None:
        """Acepta nombres de integrante alfabéticos válidos con espacios y tildes."""
        resultado = validarNombreIntegrante("Javier Infante Ángel")
        assert resultado == Exito("Javier Infante Ángel")

    def testValidarNombreIntegranteVacio(self) -> None:
        """Rechaza nombres vacíos de integrantes."""
        resultado = validarNombreIntegrante("   ")
        assert isinstance(resultado, Fallo)
        assert isinstance(resultado.obtenerError(), ErrorValidacion)

    def testValidarNombreIntegranteConNumeros(self) -> None:
        """Rechaza nombres que contengan números o símbolos."""
        resultado = validarNombreIntegrante("Carlos Bernabé 2da")
        assert isinstance(resultado, Fallo)
        assert isinstance(resultado.obtenerError(), ErrorValidacion)

    def testValidarNombreIntegranteExcedeLongitud(self) -> None:
        """Rechaza nombres de integrantes que superen 80 caracteres."""
        resultado = validarNombreIntegrante("A" * 81)
        assert isinstance(resultado, Fallo)
        assert isinstance(resultado.obtenerError(), ErrorValidacion)

    def testValidarEliminacionIntegranteValida(self) -> None:
        """Permite eliminar integrante si no es el único y no tiene tareas activas."""
        i1 = Integrante(
            "0912345678", "PROY-001", "David Párraga", CargoIntegrante.LIDER_PROYECTO
        )
        i2 = Integrante(
            "0987654321",
            "PROY-001",
            "Javier Infante",
            CargoIntegrante.DESARROLLADOR_FRONTEND,
        )
        tareas = (
            Tarea(
                idTarea="TAR-001",
                idPaquete="PAQ-001",
                titulo="Tarea asignada a David",
                cedulaResponsable=Alguno("0912345678"),
                activo=True,
            ),
        )

        resultado = validarEliminacionIntegrante("0987654321", (i1, i2), tareas)
        assert resultado == Exito("0987654321")

    def testValidarEliminacionUltimoIntegrante(self) -> None:
        """UT-VAL-06: Bloquea la eliminación si es el único integrante del proyecto."""
        i1 = Integrante(
            "0912345678", "PROY-001", "David Párraga", CargoIntegrante.LIDER_PROYECTO
        )

        resultado = validarEliminacionIntegrante("0912345678", (i1,), ())
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorReglaNegocio)
        assert error.codigo == "ULTIMO_INTEGRANTE"

    def testValidarEliminacionIntegranteConTareasActivas(self) -> None:
        """UT-VAL-05: Bloquea la eliminación si tiene tareas activas asignadas."""
        i1 = Integrante(
            "0912345678", "PROY-001", "David Párraga", CargoIntegrante.LIDER_PROYECTO
        )
        i2 = Integrante(
            "0987654321",
            "PROY-001",
            "Javier Infante",
            CargoIntegrante.DESARROLLADOR_FRONTEND,
        )
        tareas = (
            Tarea(
                idTarea="TAR-001",
                idPaquete="PAQ-001",
                titulo="Desarrollo Login",
                cedulaResponsable=Alguno("0987654321"),
                activo=True,
            ),
        )

        resultado = validarEliminacionIntegrante("0987654321", (i1, i2), tareas)
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorReglaNegocio)
        assert error.codigo == "INTEGRANTE_CON_TAREAS_ACTIVAS"

    def testValidarEliminacionIntegranteConTareasInactivasPermitido(self) -> None:
        """Permite la eliminación si las tareas asignadas están descartadas (activo = False)."""
        i1 = Integrante(
            "0912345678", "PROY-001", "David Párraga", CargoIntegrante.LIDER_PROYECTO
        )
        i2 = Integrante(
            "0987654321",
            "PROY-001",
            "Javier Infante",
            CargoIntegrante.DESARROLLADOR_FRONTEND,
        )
        tareas = (
            Tarea(
                idTarea="TAR-001",
                idPaquete="PAQ-001",
                titulo="Tarea borrada lógicamente",
                cedulaResponsable=Alguno("0987654321"),
                activo=False,
            ),
        )

        resultado = validarEliminacionIntegrante("0987654321", (i1, i2), tareas)
        assert resultado == Exito("0987654321")
