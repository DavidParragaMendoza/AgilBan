"""Pruebas unitarias para el cálculo declarativo de EDT y avance en el núcleo funcional."""

from app.core.edt import (
    agregarPaqueteAProyecto,
    calcularAvancePaquete,
    calcularEstadoPaquete,
    obtenerTareasActivas,
    renombrarPaquete,
)
from app.domain.catalogos import EstadoKanban, EstadoPaquete, TipoProyecto
from app.domain.errores import ErrorDuplicado, ErrorNoEncontrado
from app.domain.modelos import PaqueteTrabajo, Proyecto, Tarea
from app.domain.monadas import Exito, Fallo


class TestCalculoEdtYAvance:
    """Suite de pruebas para cálculos de estado y avance en paquetes de trabajo (EDT)."""

    def testObtenerTareasActivasFiltraInactivas(self) -> None:
        """Verifica que solo se retornen tareas con activo = True."""
        t1 = Tarea("TAR-001", "PAQ-001", "Activa 1", activo=True)
        t2 = Tarea("TAR-002", "PAQ-001", "Inactiva", activo=False)
        t3 = Tarea("TAR-003", "PAQ-001", "Activa 2", activo=True)
        paquete = PaqueteTrabajo(
            "PAQ-001", "PROY-001", "Paquete 1", tareas=(t1, t2, t3)
        )

        activas = obtenerTareasActivas(paquete)
        assert activas == (t1, t3)

    def testCalcularEstadoPaqueteSinTareas(self) -> None:
        """UT-EDT-01: Paquete sin tareas activas deriva en SIN_TAREAS y avance 0.0."""
        paqueteVacio = PaqueteTrabajo("PAQ-001", "PROY-001", "Vacio", tareas=())
        assert calcularEstadoPaquete(paqueteVacio) == EstadoPaquete.SIN_TAREAS
        assert calcularAvancePaquete(paqueteVacio) == 0.0

        tInactiva = Tarea("TAR-001", "PAQ-001", "Inactiva", activo=False)
        paqueteConInactivas = PaqueteTrabajo(
            "PAQ-001", "PROY-001", "Solo inactivas", tareas=(tInactiva,)
        )
        assert calcularEstadoPaquete(paqueteConInactivas) == EstadoPaquete.SIN_TAREAS
        assert calcularAvancePaquete(paqueteConInactivas) == 0.0

    def testCalcularEstadoPaqueteTodasPendientes(self) -> None:
        """UT-EDT-02: Paquete con todas tareas pendientes deriva en PENDIENTE y avance 0.0."""
        t1 = Tarea("TAR-001", "PAQ-001", "T1", estado=EstadoKanban.PENDIENTE)
        t2 = Tarea("TAR-002", "PAQ-001", "T2", estado=EstadoKanban.PENDIENTE)
        t3 = Tarea("TAR-003", "PAQ-001", "T3", estado=EstadoKanban.PENDIENTE)
        paquete = PaqueteTrabajo(
            "PAQ-001", "PROY-001", "Pendientes", tareas=(t1, t2, t3)
        )

        assert calcularEstadoPaquete(paquete) == EstadoPaquete.PENDIENTE
        assert calcularAvancePaquete(paquete) == 0.0

    def testCalcularEstadoPaqueteTodasTerminadas(self) -> None:
        """UT-EDT-03: Paquete con todas tareas terminadas deriva en TERMINADO y avance 100.0."""
        t1 = Tarea("TAR-001", "PAQ-001", "T1", estado=EstadoKanban.TERMINADA)
        t2 = Tarea("TAR-002", "PAQ-001", "T2", estado=EstadoKanban.TERMINADA)
        paquete = PaqueteTrabajo("PAQ-001", "PROY-001", "Terminadas", tareas=(t1, t2))

        assert calcularEstadoPaquete(paquete) == EstadoPaquete.TERMINADO
        assert calcularAvancePaquete(paquete) == 100.0

    def testCalcularEstadoPaqueteMixtoEnProgreso(self) -> None:
        """UT-EDT-04: Paquete con estados mixtos deriva en EN_PROGRESO y calcula avance proporcional."""
        t1 = Tarea("TAR-001", "PAQ-001", "T1", estado=EstadoKanban.PENDIENTE)
        t2 = Tarea("TAR-002", "PAQ-001", "T2", estado=EstadoKanban.EN_PROGRESO)
        t3 = Tarea("TAR-003", "PAQ-001", "T3", estado=EstadoKanban.TERMINADA)
        paquete = PaqueteTrabajo("PAQ-001", "PROY-001", "Mixto", tareas=(t1, t2, t3))

        assert calcularEstadoPaquete(paquete) == EstadoPaquete.EN_PROGRESO
        assert calcularAvancePaquete(paquete) == 33.33


class TestOperacionesInmutablesEdt:
    """Suite de pruebas para transformaciones inmutables de paquetes dentro de un proyecto."""

    def testAgregarPaqueteAProyecto(self) -> None:
        """Verifica la anexión inmutable de un paquete a un proyecto existente."""
        proyecto = Proyecto("PROY-001", "AgilBan", TipoProyecto.DESARROLLO_WEB)
        paquete = PaqueteTrabajo("PAQ-001", "PROY-001", "Planificación")

        proyectoActualizado = agregarPaqueteAProyecto(proyecto, paquete)

        assert len(proyecto.paquetes) == 0
        assert len(proyectoActualizado.paquetes) == 1
        assert proyectoActualizado.paquetes[0] == paquete
        assert proyectoActualizado is not proyecto

    def testRenombrarPaqueteExitoso(self) -> None:
        """Verifica que se actualice el nombre del paquete correctamente."""
        p1 = PaqueteTrabajo("PAQ-001", "PROY-001", "Antiguo Nombre")
        p2 = PaqueteTrabajo("PAQ-002", "PROY-001", "Otro Paquete")
        proyecto = Proyecto(
            "PROY-001", "AgilBan", TipoProyecto.DESARROLLO_WEB, paquetes=(p1, p2)
        )

        resultado = renombrarPaquete(proyecto, "PAQ-001", "Nuevo Nombre")
        assert isinstance(resultado, Exito)
        proyectoNuevo = resultado.obtenerValor()
        assert proyectoNuevo.paquetes[0].nombre == "Nuevo Nombre"
        assert proyectoNuevo.paquetes[1].nombre == "Otro Paquete"

    def testRenombrarPaqueteNoEncontrado(self) -> None:
        """Retorna ErrorNoEncontrado si el paquete no existe en el proyecto."""
        p1 = PaqueteTrabajo("PAQ-001", "PROY-001", "Paquete 1")
        proyecto = Proyecto(
            "PROY-001", "AgilBan", TipoProyecto.DESARROLLO_WEB, paquetes=(p1,)
        )

        resultado = renombrarPaquete(proyecto, "PAQ-999", "Nuevo")
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorNoEncontrado)
        assert error.identificador == "PAQ-999"

    def testRenombrarPaqueteDuplicadoEnProyecto(self) -> None:
        """Retorna ErrorDuplicado si el nuevo nombre ya existe en otro paquete del proyecto."""
        p1 = PaqueteTrabajo("PAQ-001", "PROY-001", "Diseño")
        p2 = PaqueteTrabajo("PAQ-002", "PROY-001", "Desarrollo")
        proyecto = Proyecto(
            "PROY-001", "AgilBan", TipoProyecto.DESARROLLO_WEB, paquetes=(p1, p2)
        )

        resultado = renombrarPaquete(proyecto, "PAQ-001", "desarrollo")
        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorDuplicado)
        assert error.identificador == "desarrollo"
