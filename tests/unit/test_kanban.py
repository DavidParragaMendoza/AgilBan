"""Pruebas unitarias para el motor de transiciones Kanban y devoluciones en app/core/kanban.py."""

from app.core.kanban import (
    avanzarOTareasKanban,
    esRetroceso,
    transicionesPermitidas,
)
from app.domain.catalogos import EstadoKanban
from app.domain.errores import ErrorTransicionKanban
from app.domain.modelos import Tarea
from app.domain.monadas import Alguno, Exito, Fallo, Ninguno


class TestMotorTransicionesKanban:
    """Suite de pruebas para validación exhaustiva de estados Kanban y devoluciones."""

    def testTransicionesPermitidasExhaustivo(self) -> None:
        """Verifica la matriz de transiciones permitidas según el plan técnico."""
        assert transicionesPermitidas(EstadoKanban.PENDIENTE) == (
            EstadoKanban.EN_PROGRESO,
        )
        assert transicionesPermitidas(EstadoKanban.EN_PROGRESO) == (
            EstadoKanban.EN_REVISION,
            EstadoKanban.PENDIENTE,
        )
        assert transicionesPermitidas(EstadoKanban.EN_REVISION) == (
            EstadoKanban.TERMINADA,
            EstadoKanban.EN_PROGRESO,
        )
        assert transicionesPermitidas(EstadoKanban.TERMINADA) == (
            EstadoKanban.EN_PROGRESO,
        )

    def testEsRetrocesoIdentificaDevoluciones(self) -> None:
        """Verifica la detección funcional de transiciones que constituyen retrocesos."""
        assert esRetroceso(EstadoKanban.EN_PROGRESO, EstadoKanban.PENDIENTE) is True
        assert esRetroceso(EstadoKanban.EN_REVISION, EstadoKanban.EN_PROGRESO) is True
        assert esRetroceso(EstadoKanban.TERMINADA, EstadoKanban.EN_PROGRESO) is True

        assert esRetroceso(EstadoKanban.PENDIENTE, EstadoKanban.EN_PROGRESO) is False
        assert esRetroceso(EstadoKanban.EN_PROGRESO, EstadoKanban.EN_REVISION) is False
        assert esRetroceso(EstadoKanban.EN_REVISION, EstadoKanban.TERMINADA) is False

    def testAvanceLegalSecuencial(self) -> None:
        """UT-KAN-01: Permite el avance legal secuencial registrando transición en historial."""
        tarea = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-001",
            titulo="Login",
            estado=EstadoKanban.PENDIENTE,
        )
        resultado = avanzarOTareasKanban(
            tarea=tarea,
            nuevoEstado=EstadoKanban.EN_PROGRESO,
            comentario=Ninguno(),
            timestamp="2026-10-24T00:30:00",
        )

        assert isinstance(resultado, Exito)
        tareaActualizada = resultado.obtenerValor()
        assert tareaActualizada.estado == EstadoKanban.EN_PROGRESO
        assert tareaActualizada.contadorRegresos == 0
        assert len(tareaActualizada.historial) == 1

        transicion = tareaActualizada.historial[0]
        assert transicion.idTarea == "TAR-001"
        assert transicion.estadoOrigen == EstadoKanban.PENDIENTE
        assert transicion.estadoDestino == EstadoKanban.EN_PROGRESO
        assert transicion.fechaHora == "2026-10-24T00:30:00"
        assert transicion.comentario == Ninguno()

    def testSaltoEstadoIlegal(self) -> None:
        """UT-KAN-02: Bloquea saltos no autorizados en el flujo del tablero."""
        tarea = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-001",
            titulo="Login",
            estado=EstadoKanban.PENDIENTE,
        )
        resultado = avanzarOTareasKanban(
            tarea=tarea,
            nuevoEstado=EstadoKanban.TERMINADA,
            comentario=Ninguno(),
            timestamp="2026-10-24T00:30:00",
        )

        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorTransicionKanban)
        assert error.origen == EstadoKanban.PENDIENTE
        assert error.destino == EstadoKanban.TERMINADA

    def testRetrocesoValidoConJustificacion(self) -> None:
        """UT-KAN-03: Devolución válida exige justificación, incrementa regresos y guarda historial."""
        tarea = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-001",
            titulo="Login",
            estado=EstadoKanban.EN_PROGRESO,
            contadorRegresos=0,
        )
        resultado = avanzarOTareasKanban(
            tarea=tarea,
            nuevoEstado=EstadoKanban.PENDIENTE,
            comentario=Alguno("Falta diseño de pantallas"),
            timestamp="2026-10-24T00:35:00",
        )

        assert isinstance(resultado, Exito)
        tareaDevuelta = resultado.obtenerValor()
        assert tareaDevuelta.estado == EstadoKanban.PENDIENTE
        assert tareaDevuelta.contadorRegresos == 1
        assert len(tareaDevuelta.historial) == 1
        assert tareaDevuelta.historial[0].comentario == Alguno(
            "Falta diseño de pantallas"
        )

    def testRetrocesoSinJustificacionNinguno(self) -> None:
        """UT-KAN-04: Bloquea devolución si no se proporciona justificación (Ninguno)."""
        tarea = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-001",
            titulo="Login",
            estado=EstadoKanban.EN_REVISION,
        )
        resultado = avanzarOTareasKanban(
            tarea=tarea,
            nuevoEstado=EstadoKanban.EN_PROGRESO,
            comentario=Ninguno(),
            timestamp="2026-10-24T00:35:00",
        )

        assert isinstance(resultado, Fallo)
        error = resultado.obtenerError()
        assert isinstance(error, ErrorTransicionKanban)
        assert error.origen == EstadoKanban.EN_REVISION
        assert error.destino == EstadoKanban.EN_PROGRESO

    def testRetrocesoConJustificacionVacia(self) -> None:
        """Bloquea devolución si el comentario está en blanco o solo contiene espacios."""
        tarea = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-001",
            titulo="Login",
            estado=EstadoKanban.EN_REVISION,
        )
        resultado = avanzarOTareasKanban(
            tarea=tarea,
            nuevoEstado=EstadoKanban.EN_PROGRESO,
            comentario=Alguno("    "),
            timestamp="2026-10-24T00:35:00",
        )

        assert isinstance(resultado, Fallo)
        assert isinstance(resultado.obtenerError(), ErrorTransicionKanban)

    def testRetrocesoConJustificacionExcede300Caracteres(self) -> None:
        """Bloquea devolución si el comentario supera el límite de 300 caracteres."""
        tarea = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-001",
            titulo="Login",
            estado=EstadoKanban.TERMINADA,
        )
        comentarioExcedido = "C" * 301
        resultado = avanzarOTareasKanban(
            tarea=tarea,
            nuevoEstado=EstadoKanban.EN_PROGRESO,
            comentario=Alguno(comentarioExcedido),
            timestamp="2026-10-24T00:35:00",
        )

        assert isinstance(resultado, Fallo)
        assert isinstance(resultado.obtenerError(), ErrorTransicionKanban)
