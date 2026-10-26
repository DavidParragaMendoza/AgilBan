"""Pruebas de integración para el esquema relacional e inicialización DDL en SQLite."""

import sqlite3

from app.adapters.esquemaSqlite import DDL_ESQUEMA, inicializarEsquema
from app.adapters.repositorioSqlite import (
    actualizarNombrePaquete,
    eliminarIntegrante,
    eliminarPaqueteVacio,
    guardarProyectoCompleto,
    guardarTareaConHistorial,
    recuperarProyectos,
)
from app.adapters.telemetria import (
    limpiarHistorialTelemetria,
    obtenerHistorialTelemetria,
)
from app.core.kanban import avanzarOTareasKanban, descartarTareaLogicamente
from app.domain.catalogos import (
    CargoIntegrante,
    EstadoKanban,
    PrioridadTarea,
    TipoProyecto,
)
from app.domain.modelos import Integrante, PaqueteTrabajo, Proyecto, Tarea
from app.domain.monadas import Alguno, Exito, Fallo, Ninguno


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
            "historial_creaciones",
            "secuencia_tareas",
        }
        assert tablasEsperadas.issubset(tablasCreadas)

        cursor.execute(
            "SELECT nombre, ultimo_valor FROM secuencia_tareas WHERE nombre = 'tareas';"
        )
        assert cursor.fetchone() == ("tareas", 0)

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

    def testEstructuraHistorialCreacionesYClaveUnica(self) -> None:
        """Verifica la forma del registro de creación, su clave única y la referencia a tareas."""
        conexion = sqlite3.connect(":memory:")
        resultado = inicializarEsquema(conexion)
        assert isinstance(resultado, Exito)
        cursor = conexion.cursor()

        cursor.execute("PRAGMA table_info(historial_creaciones);")
        columnasEvento = {fila[1] for fila in cursor.fetchall()}
        assert columnasEvento == {"id_tarea", "fecha_hora", "clave_solicitud"}

        cursor.execute("PRAGMA index_list(historial_creaciones);")
        indicesEvento = cursor.fetchall()
        assert any(fila[2] == 1 for fila in indicesEvento)

        cursor.execute("PRAGMA foreign_key_list(historial_creaciones);")
        clavesForaneas = cursor.fetchall()
        assert any(fila[2] == "tareas" and fila[3] == "id_tarea" for fila in clavesForaneas)
        conexion.close()

    def testMigrarEsquemaExistentePreservaDatosYInicializaSecuenciaGlobal(self) -> None:
        """Migra una base legacy sin alterar IDs ni fabricar eventos de creación."""
        conexion = sqlite3.connect(":memory:")
        conexion.executescript(
            """
            CREATE TABLE proyectos (
                id_proyecto TEXT PRIMARY KEY,
                nombre TEXT NOT NULL UNIQUE,
                tipo TEXT NOT NULL
            );
            CREATE TABLE paquetes_trabajo (
                id_paquete TEXT PRIMARY KEY,
                id_proyecto TEXT NOT NULL,
                nombre TEXT NOT NULL,
                UNIQUE (id_proyecto, nombre),
                FOREIGN KEY (id_proyecto) REFERENCES proyectos(id_proyecto)
            );
            CREATE TABLE tareas (
                id_tarea TEXT PRIMARY KEY,
                id_paquete TEXT NOT NULL,
                titulo TEXT NOT NULL,
                descripcion TEXT,
                prioridad TEXT NOT NULL,
                cedula_responsable TEXT,
                fecha_objetivo TEXT,
                estado TEXT NOT NULL DEFAULT 'Pendiente',
                contador_regresos INTEGER NOT NULL DEFAULT 0,
                activo INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (id_paquete) REFERENCES paquetes_trabajo(id_paquete)
            );
            CREATE TABLE historial_transiciones (
                id_transicion TEXT PRIMARY KEY,
                id_tarea TEXT NOT NULL,
                estado_origen TEXT NOT NULL,
                estado_destino TEXT NOT NULL,
                fecha_hora TEXT NOT NULL,
                comentario TEXT,
                FOREIGN KEY (id_tarea) REFERENCES tareas(id_tarea)
            );
            INSERT INTO proyectos VALUES ('PROY-LEGACY', 'Proyecto legacy', 'Desarrollo Web');
            INSERT INTO paquetes_trabajo VALUES ('PAQ-LEGACY', 'PROY-LEGACY', 'Paquete legacy');
            INSERT INTO tareas (id_tarea, id_paquete, titulo, prioridad) VALUES
                ('TAR-007', 'PAQ-LEGACY', 'Tarea correlativa', 'Media'),
                ('TAR-120-extra', 'PAQ-LEGACY', 'Tarea correlativa extendida', 'Alta'),
                ('TAR-99', 'PAQ-LEGACY', 'ID con menos de tres dígitos', 'Baja'),
                ('TAR-ABC', 'PAQ-LEGACY', 'ID no numérico', 'Media'),
                ('LEG-999', 'PAQ-LEGACY', 'ID de otro formato', 'Media');
            INSERT INTO historial_transiciones VALUES (
                'TRN-LEGACY',
                'TAR-007',
                'Pendiente',
                'En progreso',
                '2026-10-24T10:00:00',
                NULL
            );
            """
        )

        resultado = inicializarEsquema(conexion)
        assert isinstance(resultado, Exito)

        cursor = conexion.cursor()
        cursor.execute(
            "SELECT id_tarea FROM tareas ORDER BY id_tarea;"
        )
        assert {fila[0] for fila in cursor.fetchall()} == {
            "TAR-007",
            "TAR-120-extra",
            "TAR-99",
            "TAR-ABC",
            "LEG-999",
        }

        cursor.execute(
            "SELECT id_transicion FROM historial_transiciones;"
        )
        assert cursor.fetchall() == [("TRN-LEGACY",)]

        cursor.execute("SELECT COUNT(*) FROM historial_creaciones;")
        assert cursor.fetchone() == (0,)

        cursor.execute(
            "SELECT ultimo_valor FROM secuencia_tareas WHERE nombre = 'tareas';"
        )
        assert cursor.fetchone() == (120,)

        cursor.execute(
            "UPDATE secuencia_tareas SET ultimo_valor = 125 WHERE nombre = 'tareas';"
        )
        conexion.commit()

        resultadoRepetido = inicializarEsquema(conexion)
        assert isinstance(resultadoRepetido, Exito)

        cursor.execute(
            "SELECT ultimo_valor FROM secuencia_tareas WHERE nombre = 'tareas';"
        )
        assert cursor.fetchone() == (125,)
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


class TestRepositorioTareasHistorialYBorradoLogico:
    """Suite de integración para tareas, transiciones atómicas, historial y borrado lógico (Tarea 5.4)."""

    def setup_method(self) -> None:
        """Inicializa base de datos con proyecto base y paquete de trabajo."""
        self.conexion = sqlite3.connect(":memory:")
        inicializarEsquema(self.conexion)

        proyecto = Proyecto(
            idProyecto="PROY-KANBAN",
            nombre="Tablero AgilBan",
            tipo=TipoProyecto.DESARROLLO_WEB,
            paquetes=(PaqueteTrabajo("PAQ-KANBAN", "PROY-KANBAN", "Core Kanban"),),
            integrantes=(
                Integrante(
                    "0955555555",
                    "PROY-KANBAN",
                    "Deivy Anthony",
                    CargoIntegrante.DESARROLLADOR_FULLSTACK,
                ),
            ),
        )
        guardarProyectoCompleto(self.conexion, proyecto)

    def teardown_method(self) -> None:
        """Cierra la conexión al finalizar la prueba."""
        self.conexion.close()

    def testIT_SQL_02_TransaccionalidadRollbackAnteFallos(self) -> None:
        """IT-SQL-02: Transacción revierte completamente ante violación de clave foránea."""
        tareaInvalida = Tarea(
            idTarea="TAR-INVALIDA",
            idPaquete="PAQ-INEXISTENTE",  # Clave foránea no existe
            titulo="Tarea con paquete inválido",
            prioridad=PrioridadTarea.ALTA,
        )

        resultado = guardarTareaConHistorial(self.conexion, tareaInvalida)
        assert isinstance(resultado, Fallo)

        # Verificamos que no se insertó nada en la base de datos (garantía de ROLLBACK)
        cursor = self.conexion.cursor()
        cursor.execute("SELECT COUNT(*) FROM tareas WHERE id_tarea = 'TAR-INVALIDA'")
        assert cursor.fetchone()[0] == 0

    def testIT_SQL_03_BorradoLogicoPersistente(self) -> None:
        """IT-SQL-03: Actualizar tarea a activo = False persiste activo = 0 sin borrar el registro."""
        tareaInicial = Tarea(
            idTarea="TAR-LOGICA",
            idPaquete="PAQ-KANBAN",
            titulo="Tarea para descarte",
            prioridad=PrioridadTarea.MEDIA,
            activo=True,
        )
        resGuardar = guardarTareaConHistorial(self.conexion, tareaInicial)
        assert isinstance(resGuardar, Exito)

        # Descartar lógicamente la tarea
        tareaDescartada = descartarTareaLogicamente(tareaInicial)
        assert tareaDescartada.activo is False

        # Guardar tarea descartada
        resDescarte = guardarTareaConHistorial(self.conexion, tareaDescartada)
        assert isinstance(resDescarte, Exito)

        # Comprobar en base de datos: la fila sigue existiendo con activo = 0
        cursor = self.conexion.cursor()
        cursor.execute("SELECT activo FROM tareas WHERE id_tarea = 'TAR-LOGICA'")
        fila = cursor.fetchone()
        assert fila is not None
        assert fila[0] == 0

        # Al recuperar por la jerarquía, la tarea debe reconstruirse con activo = False
        proyectos = recuperarProyectos(self.conexion).obtenerValor()
        tareaRecuperada = proyectos[0].paquetes[0].tareas[0]
        assert tareaRecuperada.idTarea == "TAR-LOGICA"
        assert tareaRecuperada.activo is False

    def testIT_SQL_04_HistorialTransicionesConsecutivas(self) -> None:
        """IT-SQL-04: Registrar 3 transiciones consecutivas y verificar persistencia y orden cronológico."""
        tarea0 = Tarea(
            idTarea="TAR-FLUJO",
            idPaquete="PAQ-KANBAN",
            titulo="Implementar flujo completo",
            prioridad=PrioridadTarea.CRITICA,
            estado=EstadoKanban.PENDIENTE,
        )

        # Transición 1: PENDIENTE -> EN_PROGRESO
        resT1 = avanzarOTareasKanban(
            tarea0, EstadoKanban.EN_PROGRESO, Ninguno(), "2026-10-24T20:00:00"
        )
        tarea1 = resT1.obtenerValor()

        # Transición 2: EN_PROGRESO -> EN_REVISION
        resT2 = avanzarOTareasKanban(
            tarea1, EstadoKanban.EN_REVISION, Ninguno(), "2026-10-24T21:00:00"
        )
        tarea2 = resT2.obtenerValor()

        # Transición 3: EN_REVISION -> EN_PROGRESO (retroceso justificado)
        resT3 = avanzarOTareasKanban(
            tarea2,
            EstadoKanban.EN_PROGRESO,
            Alguno("Falta cobertura de tests"),
            "2026-10-24T22:00:00",
        )
        tarea3 = resT3.obtenerValor()
        assert tarea3.contadorRegresos == 1

        # Guardar la tarea con su historial acumulado
        resGuardar = guardarTareaConHistorial(self.conexion, tarea3)
        assert isinstance(resGuardar, Exito)

        # Recuperar desde la base de datos y verificar que se reconstruya íntegramente
        proyectos = recuperarProyectos(self.conexion).obtenerValor()
        tareaBD = proyectos[0].paquetes[0].tareas[0]

        assert tareaBD.idTarea == "TAR-FLUJO"
        assert tareaBD.estado == EstadoKanban.EN_PROGRESO
        assert tareaBD.contadorRegresos == 1
        assert len(tareaBD.historial) == 3

        # Verificar orden cronológico e invariantes de cada transición
        tr1, tr2, tr3 = tareaBD.historial
        assert tr1.estadoOrigen == EstadoKanban.PENDIENTE
        assert tr1.estadoDestino == EstadoKanban.EN_PROGRESO
        assert tr1.fechaHora == "2026-10-24T20:00:00"
        assert tr1.comentario == Ninguno()

        assert tr2.estadoOrigen == EstadoKanban.EN_PROGRESO
        assert tr2.estadoDestino == EstadoKanban.EN_REVISION
        assert tr2.fechaHora == "2026-10-24T21:00:00"
        assert tr2.comentario == Ninguno()

        assert tr3.estadoOrigen == EstadoKanban.EN_REVISION
        assert tr3.estadoDestino == EstadoKanban.EN_PROGRESO
        assert tr3.fechaHora == "2026-10-24T22:00:00"
        assert tr3.comentario == Alguno("Falta cobertura de tests")

    def testIT_SQL_05_RendimientoYTelemetria(self) -> None:
        """IT-SQL-05: Verificar telemetría y rendimiento (< 100 ms por operación en SQLite :memory:)."""
        limpiarHistorialTelemetria()
        for _ in range(50):
            res = recuperarProyectos(self.conexion)
            assert isinstance(res, Exito)

        historial = obtenerHistorialTelemetria()
        assert len(historial) >= 50
        for registro in historial:
            assert registro.duracionMs < 100.0
            assert registro.exitosa is True
