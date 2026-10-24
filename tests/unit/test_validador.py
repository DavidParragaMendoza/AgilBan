"""Pruebas unitarias para validaciones puras del núcleo funcional (Proyectos, Integrantes, Paquetes y Tareas)."""

from app.core.validador import (
    validarCedula,
    validarDatosTarea,
    validarEliminacionIntegrante,
    validarEliminacionPaquete,
    validarNombreIntegrante,
    validarNombrePaquete,
    validarNombreProyecto,
)
from app.domain.catalogos import CargoIntegrante
from app.domain.errores import ErrorDuplicado, ErrorReglaNegocio, ErrorValidacion
from app.domain.modelos import Integrante, PaqueteTrabajo, Tarea
from app.domain.monadas import Alguno, Exito, Fallo, Ninguno


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


class TestValidacionPaquete:
    """Suite de pruebas para validación y eliminación de paquetes de trabajo."""

    def testValidarNombrePaqueteValido(self) -> None:
        """Valida nombre de paquete dentro del rango de 1 a 80 caracteres."""
        resultado = validarNombrePaquete(
            "Diseño y Arquitectura", ("Pruebas", "Despliegue")
        )
        assert resultado == Exito("Diseño y Arquitectura")

    def testValidarNombrePaqueteVacio(self) -> None:
        """Rechaza nombres de paquete vacíos o de puros espacios."""
        resultado = validarNombrePaquete("   ", ())
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorValidacion)
        assert error.campo == "nombre"

    def testValidarNombrePaqueteExcedeLongitud(self) -> None:
        """Rechaza nombres de paquete que superen los 80 caracteres."""
        resultado = validarNombrePaquete("P" * 81, ())
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorValidacion)
        assert error.campo == "nombre"

    def testValidarNombrePaqueteDuplicadoEnProyecto(self) -> None:
        """Rechaza nombres duplicados en el mismo proyecto ignorando mayúsculas/minúsculas."""
        resultado = validarNombrePaquete("diseño", ("Diseño", "Desarrollo"))
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorDuplicado)
        assert error.entidad == "PaqueteTrabajo"

    def testValidarEliminacionPaqueteVacio(self) -> None:
        """Permite eliminar un paquete de trabajo que no tiene tareas."""
        paquete = PaqueteTrabajo("PAQ-001", "PROY-001", "Módulo Vacio", tareas=())
        resultado = validarEliminacionPaquete(paquete)
        assert resultado == Exito("PAQ-001")

    def testValidarEliminacionPaqueteConTareasBloqueado(self) -> None:
        """Bloquea la eliminación de un paquete si contiene tareas asociadas."""
        tarea = Tarea("TAR-001", "PAQ-001", "Tarea de prueba")
        paquete = PaqueteTrabajo(
            "PAQ-001", "PROY-001", "Módulo con tareas", tareas=(tarea,)
        )
        resultado = validarEliminacionPaquete(paquete)
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorReglaNegocio)
        assert error.codigo == "PAQUETE_CON_TAREAS"


class TestValidacionDatosTarea:
    """Suite de pruebas para validación de datos de entrada de una tarea."""

    def testValidarDatosTareaValidos(self) -> None:
        """Valida tarea con título, descripción y fecha objetivo correctos."""
        resultado = validarDatosTarea(
            titulo="Implementar autenticación JWT",
            descripcion=Alguno("Usar tokens con expiración de 1 hora."),
            fechaObjetivo=Alguno("2026-11-15"),
        )
        assert resultado == Exito(
            (
                "Implementar autenticación JWT",
                Alguno("Usar tokens con expiración de 1 hora."),
                Alguno("2026-11-15"),
            )
        )

    def testValidarDatosTareaConCamposOpcionalesNinguno(self) -> None:
        """Valida tarea válida cuando descripción y fecha son Ninguno."""
        resultado = validarDatosTarea(
            titulo="Refactorizar modelos",
            descripcion=Ninguno(),
            fechaObjetivo=Ninguno(),
        )
        assert resultado == Exito(("Refactorizar modelos", Ninguno(), Ninguno()))

    def testValidarDatosTareaTituloVacio(self) -> None:
        """Rechaza título vacío o solo con espacios."""
        resultado = validarDatosTarea("   ", Ninguno(), Ninguno())
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorValidacion)
        assert error.campo == "titulo"

    def testValidarDatosTareaTituloExcedeLongitud(self) -> None:
        """Rechaza título que exceda 120 caracteres."""
        resultado = validarDatosTarea("T" * 121, Ninguno(), Ninguno())
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorValidacion)
        assert error.campo == "titulo"

    def testValidarDatosTareaDescripcionExcedeLongitud(self) -> None:
        """Rechaza descripción que supere los 1.000 caracteres."""
        descLarga = "D" * 1001
        resultado = validarDatosTarea("Tarea válida", Alguno(descLarga), Ninguno())
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorValidacion)
        assert error.campo == "descripcion"

    def testValidarDatosTareaFechaInvalidaFormato(self) -> None:
        """Rechaza fechas que no sigan el formato ISO AAAA-MM-DD."""
        resultado = validarDatosTarea("Tarea válida", Ninguno(), Alguno("15/11/2026"))
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorValidacion)
        assert error.campo == "fechaObjetivo"

    def testValidarDatosTareaFechaInexistenteCalendario(self) -> None:
        """Rechaza fechas con formato numérico pero fecha calendario imposible (ej. 30 de febrero)."""
        resultado = validarDatosTarea("Tarea válida", Ninguno(), Alguno("2026-02-30"))
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorValidacion)
        assert error.campo == "fechaObjetivo"
