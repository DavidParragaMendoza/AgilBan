"""Pruebas de integración para el esquema relacional e inicialización DDL en SQLite."""

import sqlite3

from app.adapters.esquemaSqlite import DDL_ESQUEMA, inicializarEsquema
from app.adapters.repositorioSqlite import (
    actualizarNombrePaquete,
    eliminarIntegrante,
    eliminarPaqueteVacio,
    guardarProyectoCompleto,
    recuperarProyectos,
)
from app.domain.catalogos import (
    CargoIntegrante,
    TipoProyecto,
)
from app.domain.modelos import Integrante, PaqueteTrabajo, Proyecto
from app.domain.monadas import Exito, Fallo


class TestEsquemaSqlite:
    """Suite de pruebas de integración para la creación e idempotencia del esquema SQLite."""

    def testInicializarEsquemaIdempotente(self) -> None:
        """Verifica que el DDL cree todas las tablas e índices y soporte múltiples ejecuciones sin error."""
        assert "CREATE TABLE IF NOT EXISTS proyectos" in DDL_ESQUEMA
        conexion = sqlite3.connect(":memory:")

        # Primera ejecución
        resultado1 = inicializarEsquema(conexion)
        assert isinstance(resultado1, Exito)
        assert resultado1.obtenerValor() is None

        # Segunda ejecución (idempotencia garantizada por CREATE TABLE/INDEX IF NOT EXISTS)
        resultado2 = inicializarEsquema(conexion)
        assert isinstance(resultado2, Exito)

        cursor = conexion.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        tablasCreadas = {fila[0] for fila in cursor.fetchall()}

        tablasEsperadas = {
            "proyectos",
            "integrantes",
            "paquetes_trabajo",
            "tareas",
            "historial_transiciones",
        }
        assert tablasEsperadas.issubset(tablasCreadas)

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%' ORDER BY name;"
        )
        indicesCreados = {fila[0] for fila in cursor.fetchall()}
        indicesEsperados = {
            "idx_tareas_paquete",
            "idx_tareas_activo",
            "idx_historial_tarea",
        }
        assert indicesEsperados == indicesCreados

        conexion.close()

    def testClavesForaneasActivadasYRestriccion(self) -> None:
        """Verifica que foreign_keys esté activo y restrinja inserciones huérfanas."""
        conexion = sqlite3.connect(":memory:")
        resultado = inicializarEsquema(conexion)
        assert isinstance(resultado, Exito)

        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys;")
        assert cursor.fetchone()[0] == 1

        # Intentar insertar un paquete con id_proyecto inexistente debe violar FK
        try:
            cursor.execute(
                "INSERT INTO paquetes_trabajo (id_paquete, id_proyecto, nombre) VALUES ('PAQ-01', 'PROY-INEXISTENTE', 'Diseño');"
            )
            conexion.commit()
            violacionOcurrida = False
        except sqlite3.IntegrityError:
            violacionOcurrida = True

        assert violacionOcurrida is True
        conexion.close()

    def testInicializarEsquemaConexionInvalida(self) -> None:
        """Verifica que un fallo de conexión retorne Fallo con mensaje de error."""
        conexion = sqlite3.connect(":memory:")
        conexion.close()  # Cerramos la conexión para forzar error en I/O

        resultado = inicializarEsquema(conexion)
        assert isinstance(resultado, Fallo)
        assert len(resultado.obtenerError()) > 0


class TestRepositorioProyectosIntegrantesPaquetes:
    """Suite de integración para persistencia de proyectos, integrantes y paquetes (Tarea 5.3)."""

    def setup_method(self) -> None:
        """Inicializa una base de datos SQLite en memoria con esquema para cada prueba."""
        self.conexion = sqlite3.connect(":memory:")
        resultado = inicializarEsquema(self.conexion)
        assert isinstance(resultado, Exito)

    def teardown_method(self) -> None:
        """Cierra la conexión al finalizar cada prueba."""
        self.conexion.close()

    def testIT_SQL_01_CreacionYRecuperacionIntegra(self) -> None:
        """IT-SQL-01: Guardar proyecto con 2 paquetes y 2 integrantes y recuperarlo íntegramente."""
        integrante1 = Integrante(
            cedula="0911111111",
            idProyecto="PROY-001",
            nombre="David Párraga",
            cargo=CargoIntegrante.LIDER_PROYECTO,
        )
        integrante2 = Integrante(
            cedula="0922222222",
            idProyecto="PROY-001",
            nombre="Deivy Prudente",
            cargo=CargoIntegrante.DESARROLLADOR_FULLSTACK,
        )
        paquete1 = PaqueteTrabajo(
            idPaquete="PAQ-001",
            idProyecto="PROY-001",
            nombre="Arquitectura Base",
        )
        paquete2 = PaqueteTrabajo(
            idPaquete="PAQ-002",
            idProyecto="PROY-001",
            nombre="Módulo de Seguridad",
        )
        proyectoOriginal = Proyecto(
            idProyecto="PROY-001",
            nombre="AgilBan Core",
            tipo=TipoProyecto.DESARROLLO_WEB,
            paquetes=(paquete1, paquete2),
            integrantes=(integrante1, integrante2),
        )

        resGuardar = guardarProyectoCompleto(self.conexion, proyectoOriginal)
        assert isinstance(resGuardar, Exito)

        resRecuperar = recuperarProyectos(self.conexion)
        assert isinstance(resRecuperar, Exito)
        proyectosRecuperados = resRecuperar.obtenerValor()

        assert len(proyectosRecuperados) == 1
        recuperado = proyectosRecuperados[0]
        assert recuperado.idProyecto == proyectoOriginal.idProyecto
        assert recuperado.nombre == proyectoOriginal.nombre
        assert recuperado.tipo == proyectoOriginal.tipo

        # Verificar integrantes reconstruidos inmutables
        cedulas = {i.cedula for i in recuperado.integrantes}
        assert cedulas == {"0911111111", "0922222222"}

        # Verificar paquetes reconstruidos
        nombresPaquetes = {p.nombre for p in recuperado.paquetes}
        assert nombresPaquetes == {"Arquitectura Base", "Módulo de Seguridad"}

    def testActualizarNombrePaquete(self) -> None:
        """Verifica actualización exitosa de nombre de paquete y bloqueo por duplicidad."""
        proyecto = Proyecto(
            idProyecto="PROY-002",
            nombre="App Móvil Delivery",
            tipo=TipoProyecto.APLICACION_MOVIL,
            paquetes=(
                PaqueteTrabajo("PAQ-10", "PROY-002", "Diseño"),
                PaqueteTrabajo("PAQ-20", "PROY-002", "Backend"),
            ),
            integrantes=(
                Integrante(
                    "0933333333",
                    "PROY-002",
                    "Carlos Bernabé",
                    CargoIntegrante.DESARROLLADOR_BACKEND,
                ),
            ),
        )
        guardarProyectoCompleto(self.conexion, proyecto)

        # Actualización válida
        resAct = actualizarNombrePaquete(self.conexion, "PAQ-10", "Diseño UI/UX")
        assert isinstance(resAct, Exito)

        proyectos = recuperarProyectos(self.conexion).obtenerValor()
        paquetesActuales = {p.idPaquete: p.nombre for p in proyectos[0].paquetes}
        assert paquetesActuales["PAQ-10"] == "Diseño UI/UX"

        # Conflicto de nombre duplicado dentro del mismo proyecto
        resDuplicado = actualizarNombrePaquete(self.conexion, "PAQ-20", "Diseño UI/UX")
        assert isinstance(resDuplicado, Fallo)

    def testEliminarPaqueteVacioYBloqueoConTareas(self) -> None:
        """Verifica que solo se puedan eliminar paquetes sin tareas registradas."""
        proyecto = Proyecto(
            idProyecto="PROY-003",
            nombre="Portal Web",
            tipo=TipoProyecto.DESARROLLO_WEB,
            paquetes=(
                PaqueteTrabajo("PAQ-VACIO", "PROY-003", "Sin tareas"),
                PaqueteTrabajo("PAQ-CON-TAREAS", "PROY-003", "Con tareas"),
            ),
            integrantes=(
                Integrante(
                    "0944444444",
                    "PROY-003",
                    "Javier Infante",
                    CargoIntegrante.INGENIERO_QA,
                ),
            ),
        )
        guardarProyectoCompleto(self.conexion, proyecto)

        # Insertamos una tarea en PAQ-CON-TAREAS
        cursor = self.conexion.cursor()
        cursor.execute(
            """INSERT INTO tareas (id_tarea, id_paquete, titulo, prioridad, activo)
               VALUES ('TAR-99', 'PAQ-CON-TAREAS', 'Test manual', 'Media', 1)"""
        )
        self.conexion.commit()

        # Intentar eliminar paquete con tareas debe fallar
        resFallo = eliminarPaqueteVacio(self.conexion, "PAQ-CON-TAREAS")
        assert isinstance(resFallo, Fallo)

        # Eliminar paquete vacío debe tener éxito
        resExito = eliminarPaqueteVacio(self.conexion, "PAQ-VACIO")
        assert isinstance(resExito, Exito)

        proyectos = recuperarProyectos(self.conexion).obtenerValor()
        idsRestantes = [p.idPaquete for p in proyectos[0].paquetes]
        assert "PAQ-VACIO" not in idsRestantes
        assert "PAQ-CON-TAREAS" in idsRestantes

    def testEliminarIntegranteReglas(self) -> None:
        """Verifica restricciones de negocio al eliminar integrante en persistencia."""
        integrante1 = Integrante(
            "0911111111",
            "PROY-004",
            "David Párraga",
            CargoIntegrante.LIDER_PROYECTO,
        )
        integrante2 = Integrante(
            "0922222222",
            "PROY-004",
            "Deivy Prudente",
            CargoIntegrante.DESARROLLADOR_FULLSTACK,
        )
        proyecto = Proyecto(
            idProyecto="PROY-004",
            nombre="Sistema ERP",
            tipo=TipoProyecto.DESARROLLO_WEB,
            paquetes=(PaqueteTrabajo("PAQ-30", "PROY-004", "General"),),
            integrantes=(integrante1, integrante2),
        )
        guardarProyectoCompleto(self.conexion, proyecto)

        # Asignamos una tarea activa al integrante1
        cursor = self.conexion.cursor()
        cursor.execute(
            """INSERT INTO tareas (id_tarea, id_paquete, titulo, prioridad, cedula_responsable, activo)
               VALUES ('TAR-31', 'PAQ-30', 'Planificación', 'Alta', '0911111111', 1)"""
        )
        self.conexion.commit()

        # Intentar eliminar integrante1 (con tareas activas) debe fallar
        resFalloTareas = eliminarIntegrante(self.conexion, "0911111111", "PROY-004")
        assert isinstance(resFalloTareas, Fallo)

        # Eliminar integrante2 (sin tareas) debe tener éxito
        resExito = eliminarIntegrante(self.conexion, "0922222222", "PROY-004")
        assert isinstance(resExito, Exito)

        # Ahora integrante1 es el único integrante restante; intentar eliminarlo debe fallar
        resFalloUnico = eliminarIntegrante(self.conexion, "0911111111", "PROY-004")
        assert isinstance(resFalloUnico, Fallo)
