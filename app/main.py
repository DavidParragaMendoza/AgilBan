"""Punto de entrada del servidor web FastAPI y montaje de ReactPy para AgilBan.

Inicializa la aplicación FastAPI sin endpoints REST manuales, verifica la base
de datos relacional SQLite agilban.db e inyecta la CDN de Tailwind CSS y tipografías
modernas en el encabezado HTML para servir la interfaz web reactiva.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from fastapi import FastAPI
from reactpy import html
from reactpy.backend.fastapi import Options, configure
from reactpy.types import VdomDict

from app.adapters.esquemaSqlite import inicializarEsquema
from app.domain.monadas import Fallo
from app.ui.web.app import componenteApp

RUTA_BASE_DATOS_DEFECTO: str = "agilban.db"

_conexionGlobal: sqlite3.Connection | None = None


def obtenerConexionApp(
    rutaBaseDatos: str = RUTA_BASE_DATOS_DEFECTO,
) -> sqlite3.Connection:
    """Obtiene o inicializa la conexión transaccional con la base de datos SQLite."""
    global _conexionGlobal
    if _conexionGlobal is None:
        _conexionGlobal = sqlite3.connect(rutaBaseDatos, check_same_thread=False)
        resultado = inicializarEsquema(_conexionGlobal)
        if isinstance(resultado, Fallo):
            raise RuntimeError(
                f"Error crítico al inicializar el esquema relacional: {resultado.error}"
            )
    return _conexionGlobal


def crearElementosEncabezadoHtml() -> Sequence[VdomDict]:
    """Genera los elementos del encabezado HTML incluyendo título, Tailwind CSS y tipografía Inter."""
    return (
        html.title("AgilBan — Gestión Ágil Local"),
        html.meta(
            {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
        ),
        html.link(
            {
                "rel": "preconnect",
                "href": "https://fonts.googleapis.com",
            }
        ),
        html.link(
            {
                "rel": "preconnect",
                "href": "https://fonts.gstatic.com",
                "crossorigin": "anonymous",
            }
        ),
        html.link(
            {
                "rel": "stylesheet",
                "href": "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
            }
        ),
        html.script({"src": "https://cdn.tailwindcss.com"}),
    )


def crearAplicacionWeb(rutaBaseDatos: str = RUTA_BASE_DATOS_DEFECTO) -> FastAPI:
    """Fabrica y configura la instancia de FastAPI montando el componente raíz de ReactPy."""
    conexion = obtenerConexionApp(rutaBaseDatos)

    # Se deshabilitan los endpoints automáticos de documentación REST para cumplir RNF-03
    aplicacion = FastAPI(
        title="AgilBan Web",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    opcionesConfiguracion = Options(
        head=crearElementosEncabezadoHtml(),
    )

    def constructorRaiz():
        return componenteApp(conexion=conexion)

    configure(aplicacion, constructorRaiz, opcionesConfiguracion)

    return aplicacion


# Instancia principal accesible por servidores ASGI (ej. uvicorn app.main:app)
app: FastAPI = crearAplicacionWeb()
