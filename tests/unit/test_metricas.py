"""Pruebas unitarias para métricas analíticas, avance global y cuellos de botella en app/core/metricas.py."""

from app.core.metricas import (
    auditarCuellosDeBotella,
    calcularAvanceGlobal,
    calcularCargaIntegrantes,
    calcularResumenTareas,
)
from app.domain.catalogos import CargoIntegrante, EstadoKanban
from app.domain.modelos import Integrante, Tarea
from app.domain.monadas import Alguno, Ninguno


class TestMetricasAnaliticas:
    """Suite de pruebas para transformaciones declarativas de analítica y métricas."""

    def testCalcularResumenTareas(self) -> None:
        """Verifica el resumen cuantitativo con desglose por columnas y estado de activación."""
        tareas = (
            Tarea(
                idTarea="T1",
                idPaquete="P1",
                titulo="T1",
                estado=EstadoKanban.PENDIENTE,
                activo=True,
            ),
            Tarea(
                idTarea="T2",
                idPaquete="P1",
                titulo="T2",
                estado=EstadoKanban.EN_PROGRESO,
                activo=True,
            ),
            Tarea(
                idTarea="T3",
                idPaquete="P1",
                titulo="T3",
                estado=EstadoKanban.EN_REVISION,
                activo=True,
            ),
            Tarea(
                idTarea="T4",
                idPaquete="P1",
                titulo="T4",
                estado=EstadoKanban.TERMINADA,
                activo=True,
            ),
            Tarea(
                idTarea="T5",
                idPaquete="P1",
                titulo="T5",
                estado=EstadoKanban.PENDIENTE,
                activo=False,
            ),
        )

        resumen = calcularResumenTareas(tareas)

        assert resumen["totalActivas"] == 4
        assert resumen["totalInactivas"] == 1
        assert resumen[EstadoKanban.PENDIENTE.value] == 1
        assert resumen[EstadoKanban.EN_PROGRESO.value] == 1
        assert resumen[EstadoKanban.EN_REVISION.value] == 1
        assert resumen[EstadoKanban.TERMINADA.value] == 1

    def testCalcularResumenTareasVacio(self) -> None:
        """Verifica que sobre una tupla vacía todos los conteos resulten en cero."""
        resumen = calcularResumenTareas(())

        assert resumen["totalActivas"] == 0
        assert resumen["totalInactivas"] == 0
        assert resumen[EstadoKanban.PENDIENTE.value] == 0
        assert resumen[EstadoKanban.EN_PROGRESO.value] == 0
        assert resumen[EstadoKanban.EN_REVISION.value] == 0
        assert resumen[EstadoKanban.TERMINADA.value] == 0

    def testCalcularAvanceGlobalSinTareas(self) -> None:
        """UT-MET-01: Proyecto sin tareas activas reporta 0.0% evitando excepción de división por cero."""
        assert calcularAvanceGlobal(()) == 0.0

        tareasSoloInactivas = (
            Tarea(
                idTarea="T1",
                idPaquete="P1",
                titulo="T1",
                estado=EstadoKanban.TERMINADA,
                activo=False,
            ),
        )
        assert calcularAvanceGlobal(tareasSoloInactivas) == 0.0

    def testCalcularAvanceGlobalConTareas(self) -> None:
        """Calcula el porcentaje de tareas terminadas sobre el total de activas."""
        tareas = (
            Tarea(
                idTarea="T1",
                idPaquete="P1",
                titulo="T1",
                estado=EstadoKanban.TERMINADA,
                activo=True,
            ),
            Tarea(
                idTarea="T2",
                idPaquete="P1",
                titulo="T2",
                estado=EstadoKanban.EN_PROGRESO,
                activo=True,
            ),
            Tarea(
                idTarea="T3",
                idPaquete="P1",
                titulo="T3",
                estado=EstadoKanban.TERMINADA,
                activo=True,
            ),
            Tarea(
                idTarea="T4",
                idPaquete="P1",
                titulo="T4",
                estado=EstadoKanban.PENDIENTE,
                activo=True,
            ),
            # Tarea inactiva terminada no debe sumar al porcentaje de activas
            Tarea(
                idTarea="T5",
                idPaquete="P1",
                titulo="T5",
                estado=EstadoKanban.TERMINADA,
                activo=False,
            ),
        )

        # 2 terminadas activas de 4 tareas activas = 50.0%
        avance = calcularAvanceGlobal(tareas)
        assert avance == 50.0

    def testCalcularCargaIntegrantes(self) -> None:
        """Calcula la distribución de carga asignada y completada por integrante."""
        integrantes = (
            Integrante(
                cedula="0911111111",
                idProyecto="PROY-001",
                nombre="David Párraga",
                cargo=CargoIntegrante.LIDER_PROYECTO,
            ),
            Integrante(
                cedula="0922222222",
                idProyecto="PROY-001",
                nombre="Deivy Prudente",
                cargo=CargoIntegrante.DESARROLLADOR_FULLSTACK,
            ),
            Integrante(
                cedula="0933333333",
                idProyecto="PROY-001",
                nombre="Carlos Bernabé",
                cargo=CargoIntegrante.DESARROLLADOR_BACKEND,
            ),
        )

        tareas = (
            Tarea(
                idTarea="T1",
                idPaquete="P1",
                titulo="T1",
                cedulaResponsable=Alguno("0911111111"),
                estado=EstadoKanban.TERMINADA,
                activo=True,
            ),
            Tarea(
                idTarea="T2",
                idPaquete="P1",
                titulo="T2",
                cedulaResponsable=Alguno("0911111111"),
                estado=EstadoKanban.EN_PROGRESO,
                activo=True,
            ),
            Tarea(
                idTarea="T3",
                idPaquete="P1",
                titulo="T3",
                cedulaResponsable=Alguno("0922222222"),
                estado=EstadoKanban.TERMINADA,
                activo=True,
            ),
            # Tarea inactiva no debe contabilizarse en la carga activa
            Tarea(
                idTarea="T4",
                idPaquete="P1",
                titulo="T4",
                cedulaResponsable=Alguno("0922222222"),
                estado=EstadoKanban.TERMINADA,
                activo=False,
            ),
            # Tarea sin asignar
            Tarea(
                idTarea="T5",
                idPaquete="P1",
                titulo="T5",
                cedulaResponsable=Ninguno(),
                estado=EstadoKanban.PENDIENTE,
                activo=True,
            ),
        )

        carga = calcularCargaIntegrantes(integrantes, tareas)

        assert carga["0911111111"] == {"asignadas": 2, "terminadas": 1}
        assert carga["0922222222"] == {"asignadas": 1, "terminadas": 1}
        assert carga["0933333333"] == {"asignadas": 0, "terminadas": 0}

    def testAuditarCuellosDeBotella(self) -> None:
        """UT-MET-02: Filtra tareas con regresos > 0 y las ordena descendentemente por contador."""
        tareas = (
            Tarea(
                idTarea="T-CERO",
                idPaquete="P1",
                titulo="Sin regresos",
                contadorRegresos=0,
                activo=True,
            ),
            Tarea(
                idTarea="T-UNO",
                idPaquete="P1",
                titulo="Un regreso",
                contadorRegresos=1,
                activo=True,
            ),
            Tarea(
                idTarea="T-TRES",
                idPaquete="P1",
                titulo="Tres regresos",
                contadorRegresos=3,
                activo=True,
            ),
            Tarea(
                idTarea="T-DOS",
                idPaquete="P1",
                titulo="Dos regresos",
                contadorRegresos=2,
                activo=True,
            ),
            # Tarea inactiva con regresos no debe aparecer en cuellos de botella activos
            Tarea(
                idTarea="T-INACTIVA",
                idPaquete="P1",
                titulo="Inactiva con regresos",
                contadorRegresos=4,
                activo=False,
            ),
        )

        cuellos = auditarCuellosDeBotella(tareas)
        idsOrdenados = tuple(t.idTarea for t in cuellos)

        assert idsOrdenados == ("T-TRES", "T-DOS", "T-UNO")
        assert all(t.contadorRegresos > 0 for t in cuellos)
        assert all(t.activo for t in cuellos)

    def testAuditarCuellosDeBotellaSinRegresos(self) -> None:
        """Retorna tupla vacía cuando ninguna tarea activa presenta regresos en el tablero."""
        tareas = (
            Tarea(
                idTarea="T1",
                idPaquete="P1",
                titulo="T1",
                contadorRegresos=0,
                activo=True,
            ),
        )
        assert auditarCuellosDeBotella(tareas) == ()
