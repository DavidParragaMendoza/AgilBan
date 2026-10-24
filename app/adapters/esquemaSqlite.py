# ruff: noqa: N999
"""Módulo de definición del esquema relacional DDL e inicialización en SQLite3.

Define las tablas, restricciones de clave foránea e índices analíticos
para garantizar la persistencia atómica y el borrado lógico.
"""

from __future__ import annotations

import sqlite3

from app.adapters.telemetria import cronometrarOperacion
from app.domain.monadas import Exito, Fallo, Resultado

DDL_ESQUEMA: str = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS proyectos (
    id_proyecto TEXT PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS integrantes (
    cedula TEXT NOT NULL,
    id_proyecto TEXT NOT NULL,
    nombre TEXT NOT NULL,
    cargo TEXT NOT NULL,
    PRIMARY KEY (cedula, id_proyecto),
    FOREIGN KEY (id_proyecto) REFERENCES proyectos(id_proyecto) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS paquetes_trabajo (
    id_paquete TEXT PRIMARY KEY,
    id_proyecto TEXT NOT NULL,
    nombre TEXT NOT NULL,
    UNIQUE (id_proyecto, nombre),
    FOREIGN KEY (id_proyecto) REFERENCES proyectos(id_proyecto) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS tareas (
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
    FOREIGN KEY (id_paquete) REFERENCES paquetes_trabajo(id_paquete) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS historial_transiciones (
    id_transicion TEXT PRIMARY KEY,
    id_tarea TEXT NOT NULL,
    estado_origen TEXT NOT NULL,
    estado_destino TEXT NOT NULL,
    fecha_hora TEXT NOT NULL,
    comentario TEXT,
    FOREIGN KEY (id_tarea) REFERENCES tareas(id_tarea) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_tareas_paquete ON tareas(id_paquete);
CREATE INDEX IF NOT EXISTS idx_tareas_activo ON tareas(activo);
CREATE INDEX IF NOT EXISTS idx_historial_tarea ON historial_transiciones(id_tarea);
"""


@cronometrarOperacion(nombrePersonalizado="inicializarEsquema")
def inicializarEsquema(conexion: sqlite3.Connection) -> Resultado[None, str]:
    """Ejecuta el script DDL de forma idempotente habilitando claves foráneas."""
    try:
        conexion.execute("PRAGMA foreign_keys = ON;")
        conexion.executescript(DDL_ESQUEMA)
        return Exito(None)
    except sqlite3.Error as error:
        return Fallo(f"Error al inicializar el esquema SQLite: {error}")
