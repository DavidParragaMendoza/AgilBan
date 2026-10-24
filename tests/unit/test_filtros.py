"""Pruebas unitarias para filtros analíticos, closures, HOF y lambdas en app/core/filtros.py."""

from app.core.filtros import (
    crearCriterioFiltro,
    filtrarTareas,
    ordenarPorFecha,
    ordenarPorPrioridad,
)
from app.domain.catalogos import EstadoKanban, PrioridadTarea
from app.domain.modelos import Tarea
from app.domain.monadas import Alguno, Ninguno


class TestFiltrosTareas:
    """Suite de pruebas para closures y funciones de orden superior (HOF) de filtrado."""

    def _crearTareasPrueba(self) -> tuple[Tarea, ...]:
        """Genera una colección diversa de tareas inmutables para pruebas de consulta analítica."""
        return (
            Tarea(
                idTarea="TAR-001",
                idPaquete="PAQ-001",
                titulo="Diseño de interfaz",
                prioridad=PrioridadTarea.ALTA,
                cedulaResponsable=Alguno("0912345678"),
                fechaObjetivo=Alguno("2026-10-20"),
                estado=EstadoKanban.EN_PROGRESO,
                activo=True,
            ),
            Tarea(
                idTarea="TAR-002",
                idPaquete="PAQ-001",
                titulo="Servicio de autenticación",
                prioridad=PrioridadTarea.CRITICA,
                cedulaResponsable=Alguno("0912345678"),
                fechaObjetivo=Alguno("2026-10-15"),
                estado=EstadoKanban.TERMINADA,
                activo=True,
            ),
            Tarea(
                idTarea="TAR-003",
                idPaquete="PAQ-001",
                titulo="Documentación técnica",
                prioridad=PrioridadTarea.BAJA,
                cedulaResponsable=Alguno("0987654321"),
                fechaObjetivo=Alguno("2026-10-10"),
                estado=EstadoKanban.PENDIENTE,
                activo=True,
            ),
            Tarea(
                idTarea="TAR-004",
                idPaquete="PAQ-001",
                titulo="Optimización de consultas",
                prioridad=PrioridadTarea.MEDIA,
                cedulaResponsable=Ninguno(),
                fechaObjetivo=Alguno("2026-10-30"),
                estado=EstadoKanban.EN_REVISION,
                activo=True,
            ),
            Tarea(
                idTarea="TAR-005",
                idPaquete="PAQ-001",
                titulo="Refactorización obsoleta",
                prioridad=PrioridadTarea.ALTA,
                cedulaResponsable=Alguno("0912345678"),
                fechaObjetivo=Ninguno(),
                estado=EstadoKanban.PENDIENTE,
                activo=False,
            ),
        )

    def testFiltradoCombinadoEstadoYPrioridad(self) -> None:
        """UT-FIL-01: Filtrado combinado por estado EN_PROGRESO y prioridad ALTA."""
        tareas = self._crearTareasPrueba()
        criterio = crearCriterioFiltro(
            estado=Alguno(EstadoKanban.EN_PROGRESO),
            cedula=Ninguno(),
            prioridad=Alguno(PrioridadTarea.ALTA),
            soloVencidas=False,
            soloInactivas=False,
            fechaReferencia="2026-10-24",
        )
        resultado = filtrarTareas(tareas, criterio)

        assert len(resultado) == 1
        assert resultado[0].idTarea == "TAR-001"
        assert resultado[0].estado == EstadoKanban.EN_PROGRESO
        assert resultado[0].prioridad == PrioridadTarea.ALTA

    def testFiltradoPorResponsable(self) -> None:
        """Verifica que el closure capture la cédula y filtre exactamente las tareas asignadas activas."""
        tareas = self._crearTareasPrueba()
        criterio = crearCriterioFiltro(
            estado=Ninguno(),
            cedula=Alguno("0987654321"),
            prioridad=Ninguno(),
            soloVencidas=False,
            soloInactivas=False,
            fechaReferencia="2026-10-24",
        )
        resultado = filtrarTareas(tareas, criterio)

        assert len(resultado) == 1
        assert resultado[0].idTarea == "TAR-003"
        assert resultado[0].cedulaResponsable == Alguno("0987654321")

    def testFiltradoTareasVencidas(self) -> None:
        """Filtra tareas activas con fecha < fechaReferencia que no estén terminadas."""
        tareas = self._crearTareasPrueba()
        # TAR-001: 2026-10-20, EN_PROGRESO (vencida respecto a 2026-10-24)
        # TAR-002: 2026-10-15, TERMINADA (no cuenta como vencida operativa)
        # TAR-003: 2026-10-10, PENDIENTE (vencida respecto a 2026-10-24)
        # TAR-004: 2026-10-30 (no vencida)
        # TAR-005: inactiva
        criterio = crearCriterioFiltro(
            estado=Ninguno(),
            cedula=Ninguno(),
            prioridad=Ninguno(),
            soloVencidas=True,
            soloInactivas=False,
            fechaReferencia="2026-10-24",
        )
        resultado = filtrarTareas(tareas, criterio)

        idsVencidas = tuple(t.idTarea for t in resultado)
        assert idsVencidas == ("TAR-001", "TAR-003")

    def testFiltradoSoloInactivas(self) -> None:
        """Filtra tareas que han sido descartadas lógicamente (activo = False)."""
        tareas = self._crearTareasPrueba()
        criterio = crearCriterioFiltro(
            estado=Ninguno(),
            cedula=Ninguno(),
            prioridad=Ninguno(),
            soloVencidas=False,
            soloInactivas=True,
            fechaReferencia="2026-10-24",
        )
        resultado = filtrarTareas(tareas, criterio)

        assert len(resultado) == 1
        assert resultado[0].idTarea == "TAR-005"
        assert resultado[0].activo is False

    def testFiltradoSinCriteriosRetornaTodasActivas(self) -> None:
        """Si todos los opcionales son Ninguno y no se filtran vencidas ni inactivas, retorna todas las activas."""
        tareas = self._crearTareasPrueba()
        criterio = crearCriterioFiltro(
            estado=Ninguno(),
            cedula=Ninguno(),
            prioridad=Ninguno(),
            soloVencidas=False,
            soloInactivas=False,
            fechaReferencia="2026-10-24",
        )
        resultado = filtrarTareas(tareas, criterio)

        assert len(resultado) == 4
        assert all(t.activo for t in resultado)

    def testFiltradoSinCoincidenciasRetornaVacio(self) -> None:
        """Retorna tupla vacía cuando ninguna tarea cumple los criterios especificados."""
        tareas = self._crearTareasPrueba()
        criterio = crearCriterioFiltro(
            estado=Alguno(EstadoKanban.TERMINADA),
            cedula=Alguno("9999999999"),
            prioridad=Ninguno(),
            soloVencidas=False,
            soloInactivas=False,
            fechaReferencia="2026-10-24",
        )
        resultado = filtrarTareas(tareas, criterio)
        assert resultado == ()


class TestOrdenamientoTareas:
    """Suite de pruebas para expresiones lambda y ordenamiento inmutable."""

    def testOrdenarPorPrioridadJerarquica(self) -> None:
        """UT-FIL-02: Ordena descendentemente según la jerarquía Crítica > Alta > Media > Baja."""
        tareas = (
            Tarea(
                idTarea="T1",
                idPaquete="P1",
                titulo="T1",
                prioridad=PrioridadTarea.BAJA,
            ),
            Tarea(
                idTarea="T2",
                idPaquete="P1",
                titulo="T2",
                prioridad=PrioridadTarea.CRITICA,
            ),
            Tarea(
                idTarea="T3",
                idPaquete="P1",
                titulo="T3",
                prioridad=PrioridadTarea.MEDIA,
            ),
            Tarea(
                idTarea="T4",
                idPaquete="P1",
                titulo="T4",
                prioridad=PrioridadTarea.ALTA,
            ),
        )

        resultado = ordenarPorPrioridad(tareas)
        prioridadesOrdenadas = tuple(t.prioridad for t in resultado)

        assert prioridadesOrdenadas == (
            PrioridadTarea.CRITICA,
            PrioridadTarea.ALTA,
            PrioridadTarea.MEDIA,
            PrioridadTarea.BAJA,
        )

    def testOrdenarPorPrioridadColeccionVacia(self) -> None:
        """Verifica que ordenar una colección vacía devuelve una tupla vacía sin errores."""
        assert ordenarPorPrioridad(()) == ()

    def testOrdenarPorFechaCronologicaAscendente(self) -> None:
        """Ordena ascendentemente por fecha objetivo, situando al final las tareas sin fecha."""
        tareas = (
            Tarea(
                idTarea="T1",
                idPaquete="P1",
                titulo="T1",
                fechaObjetivo=Alguno("2026-10-30"),
            ),
            Tarea(
                idTarea="T2",
                idPaquete="P1",
                titulo="T2",
                fechaObjetivo=Ninguno(),
            ),
            Tarea(
                idTarea="T3",
                idPaquete="P1",
                titulo="T3",
                fechaObjetivo=Alguno("2026-10-10"),
            ),
            Tarea(
                idTarea="T4",
                idPaquete="P1",
                titulo="T4",
                fechaObjetivo=Alguno("2026-10-20"),
            ),
        )

        resultado = ordenarPorFecha(tareas)
        idsOrdenados = tuple(t.idTarea for t in resultado)

        assert idsOrdenados == ("T3", "T4", "T1", "T2")

    def testOrdenarPorFechaColeccionVacia(self) -> None:
        """Verifica que ordenar por fecha una colección vacía devuelve tupla vacía."""
        assert ordenarPorFecha(()) == ()
