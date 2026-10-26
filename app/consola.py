"""Punto de entrada de consola y arranque del sistema AgilBan (CLI / REPL).

Inicializa la base de datos SQLite agilban.db, establece la integridad
referencial y lanza el bucle interactivo del menú principal.
"""

from __future__ import annotations

import sqlite3
import sys
from collections.abc import Callable

from app.adapters.esquemaSqlite import inicializarEsquema
from app.domain.monadas import Fallo
from app.ui.consola import ejecutarMenuPrincipal

RUTA_BASE_DATOS_DEFECTO: str = "agilban.db"


def iniciarAplicacion(
    rutaBaseDatos: str = RUTA_BASE_DATOS_DEFECTO,
    lector: Callable[[str], str] = input,
    emisor: Callable[[str], None] = print,
) -> int:
    """Inicializa la persistencia relacional y arranca el bucle interactivo de la aplicación."""
    try:
        conexion = sqlite3.connect(rutaBaseDatos)
    except sqlite3.Error as err:
        emisor(
            f"❌ Error crítico al conectar con la base de datos SQLite '{rutaBaseDatos}': {err}"
        )
        return 1

    try:
        resEsquema = inicializarEsquema(conexion)
        if isinstance(resEsquema, Fallo):
            emisor(
                f"❌ Error al inicializar el esquema de base de datos: {resEsquema.error}"
            )
            return 1

        ejecutarMenuPrincipal(conexion, lector=lector, emisor=emisor)
        return 0
    except KeyboardInterrupt:
        emisor(
            "\n\n⚠️  Sesión interrumpida por el usuario. Saliendo de AgilBan limpiamente."
        )
        return 0
    finally:
        conexion.close()


def main() -> None:
    """Función de arranque ejecutable para la CLI."""
    sys.exit(iniciarAplicacion())


if __name__ == "__main__":
    main()
