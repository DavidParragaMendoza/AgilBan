"""Pruebas unitarias para las entidades inmutables del dominio de AgilBan."""

from dataclasses import FrozenInstanceError, replace

import pytest

from app.domain.catalogos import (
    CargoIntegrante,
    EstadoKanban,
    PrioridadTarea,
    TipoProyecto,
)
from app.domain.modelos import (
    EventoCreacionTarea,
    Integrante,
    PaqueteTrabajo,
    Proyecto,
    Tarea,
    TransicionHistorial,
)
from app.domain.monadas import Alguno, Ninguno


class TestModelosDominio:
    """Suite de pruebas para las entidades inmutables del dominio."""

    def testCreacionEventoCreacionTareaInmutable(self) -> None:
        """Verifica que el evento de creación conserva su ID y marca temporal."""
        evento = EventoCreacionTarea(
            idTarea="TAR-001",
            fechaHora="2026-10-26T07:30:00",
        )

        assert evento.idTarea == "TAR-001"
        assert evento.fechaHora == "2026-10-26T07:30:00"
        with pytest.raises(FrozenInstanceError):
            evento.fechaHora = "2026-10-26T08:00:00"  # type: ignore

    def testCreacionTransicionHistorial(self) -> None:
        """Verifica la instanciación de TransicionHistorial con comentario opcional."""
        transicion = TransicionHistorial(
            idTransicion="TRN-001",
            idTarea="TAR-001",
            estadoOrigen=EstadoKanban.PENDIENTE,
            estadoDestino=EstadoKanban.EN_PROGRESO,
            fechaHora="2026-10-23T10:00:00",
            comentario=Ninguno(),
        )
        assert transicion.idTransicion == "TRN-001"
        assert transicion.estadoOrigen == EstadoKanban.PENDIENTE
        assert transicion.estadoDestino == EstadoKanban.EN_PROGRESO
        assert transicion.comentario == Ninguno()

    def testCreacionTareaConValoresPorDefecto(self) -> None:
        """Verifica que Tarea establezca los valores por defecto esperados."""
        tarea = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-001",
            titulo="Configurar base de datos",
        )
        assert tarea.idTarea == "TAR-001"
        assert tarea.idPaquete == "PAQ-001"
        assert tarea.titulo == "Configurar base de datos"
        assert tarea.descripcion == Ninguno()
        assert tarea.prioridad == PrioridadTarea.MEDIA
        assert tarea.cedulaResponsable == Ninguno()
        assert tarea.fechaObjetivo == Ninguno()
        assert tarea.estado == EstadoKanban.PENDIENTE
        assert tarea.contadorRegresos == 0
        assert tarea.activo is True
        assert tarea.historial == ()
        assert tarea.eventoCreacion == Ninguno()

    def testTareaConEventoCreacionYSinTransicionInicial(self) -> None:
        """Verifica que una tarea nueva conserva el evento sin inventar transición."""
        evento = EventoCreacionTarea(
            idTarea="TAR-001",
            fechaHora="2026-10-26T07:30:00",
        )
        tarea = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-001",
            titulo="Configurar base de datos",
            eventoCreacion=Alguno(evento),
        )

        assert tarea.eventoCreacion == Alguno(evento)
        assert tarea.historial == ()

    def testCreacionPaqueteTrabajoEIntegrante(self) -> None:
        """Verifica la creación de PaqueteTrabajo e Integrante."""
        integrante = Integrante(
            cedula="0912345678",
            idProyecto="PROY-001",
            nombre="Carlos Bernabé",
            cargo=CargoIntegrante.DESARROLLADOR_FULLSTACK,
        )
        paquete = PaqueteTrabajo(
            idPaquete="PAQ-001",
            idProyecto="PROY-001",
            nombre="Módulo de Seguridad",
        )
        assert integrante.cedula == "0912345678"
        assert integrante.cargo == CargoIntegrante.DESARROLLADOR_FULLSTACK
        assert paquete.nombre == "Módulo de Seguridad"
        assert paquete.tareas == ()

    def testCreacionProyectoJerarquico(self) -> None:
        """Verifica la construcción inmutable jerárquica de Proyecto."""
        tarea = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-001",
            titulo="Diseño UI",
            descripcion=Alguno("Mockups en Stitch"),
            prioridad=PrioridadTarea.ALTA,
        )
        paquete = PaqueteTrabajo(
            idPaquete="PAQ-001",
            idProyecto="PROY-001",
            nombre="Planificación",
            tareas=(tarea,),
        )
        integrante = Integrante(
            cedula="0987654321",
            idProyecto="PROY-001",
            nombre="Deivy Prudente",
            cargo=CargoIntegrante.DESARROLLADOR_BACKEND,
        )
        proyecto = Proyecto(
            idProyecto="PROY-001",
            nombre="AgilBan Web",
            tipo=TipoProyecto.DESARROLLO_WEB,
            paquetes=(paquete,),
            integrantes=(integrante,),
        )

        assert proyecto.nombre == "AgilBan Web"
        assert len(proyecto.paquetes) == 1
        assert len(proyecto.integrantes) == 1
        assert isinstance(proyecto.paquetes, tuple)
        assert isinstance(proyecto.integrantes, tuple)
        assert isinstance(proyecto.paquetes[0].tareas, tuple)
        assert proyecto.paquetes[0].tareas[0].titulo == "Diseño UI"

    def testInmutabilidadEstrictaEntidades(self) -> None:
        """Comprueba que intentar mutar atributos lance FrozenInstanceError."""
        tarea = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-001",
            titulo="Original",
        )
        with pytest.raises(FrozenInstanceError):
            tarea.titulo = "Modificado"  # type: ignore

        proyecto = Proyecto(
            idProyecto="PROY-001",
            nombre="Original",
            tipo=TipoProyecto.DESARROLLO_WEB,
        )
        with pytest.raises(FrozenInstanceError):
            proyecto.nombre = "Nuevo"  # type: ignore

    def testTransformacionInmutableConReplace(self) -> None:
        """Verifica que las actualizaciones generen nuevas instancias inmutables con replace."""
        tareaInicial = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-001",
            titulo="Tarea Inicial",
            estado=EstadoKanban.PENDIENTE,
        )
        tareaAvanzada = replace(tareaInicial, estado=EstadoKanban.EN_PROGRESO)

        assert tareaInicial.estado == EstadoKanban.PENDIENTE
        assert tareaAvanzada.estado == EstadoKanban.EN_PROGRESO
        assert tareaAvanzada.idTarea == tareaInicial.idTarea
        assert tareaInicial is not tareaAvanzada

    def testPatternMatchingModelos(self) -> None:
        """Comprueba el soporte de desempaquetado con pattern matching estructural."""

        def describirTarea(t: Tarea) -> str:
            match t:
                case Tarea(idTarea=i, estado=EstadoKanban.EN_PROGRESO):
                    return f"{i} en curso"
                case Tarea(idTarea=i, estado=EstadoKanban.PENDIENTE):
                    return f"{i} por hacer"
                case _:
                    return "Otro estado"

        t1 = Tarea("TAR-001", "PAQ-001", "T1", estado=EstadoKanban.EN_PROGRESO)
        t2 = Tarea("TAR-002", "PAQ-001", "T2", estado=EstadoKanban.PENDIENTE)

        assert describirTarea(t1) == "TAR-001 en curso"
        assert describirTarea(t2) == "TAR-002 por hacer"
