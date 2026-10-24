"""Pruebas de integración para el esquema relacional e inicialización DDL en SQLite."""

import sqlite3

from app.adapters.esquemaSqlite import DDL_ESQUEMA, inicializarEsquema
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
