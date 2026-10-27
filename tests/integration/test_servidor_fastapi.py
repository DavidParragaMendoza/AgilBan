"""Pruebas de integración para la inicialización y montaje del servidor web FastAPI y ReactPy.

Verifica la Tarea 1.1 de la Fase 2:
- Arranque del servidor FastAPI sin advertencias.
- Montaje del componente raíz de ReactPy mediante configure(app, componenteApp).
- Inyección de CDN de Tailwind CSS y tipografías en el encabezado HTML.
- Respuesta HTTP 200 al acceder a la raíz '/'.
- Conexión e inicialización transaccional de SQLite.
- Ausencia de endpoints REST manuales (RNF-03 y Constitución).
"""

from __future__ import annotations

import sqlite3

from starlette.testclient import TestClient


def testServidorFastApiArrancaYRespondeHttp200() -> None:
    """Verifica que la aplicación FastAPI esté configurada y responda con código HTTP 200 en la raíz."""
    from app.main import app

    cliente = TestClient(app)
    respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers.get("content-type", "")


def testEncabezadoHtmlIncluyeTailwindYTipografias() -> None:
    """Verifica que el HTML servido inyecte la CDN de Tailwind CSS, tipografías y título oficial."""
    from app.main import app

    cliente = TestClient(app)
    respuesta = cliente.get("/")

    cuerpo = respuesta.text
    assert "cdn.tailwindcss.com" in cuerpo
    assert "fonts.googleapis.com" in cuerpo
    assert "Inter" in cuerpo or "Roboto" in cuerpo
    assert "<title>AgilBan" in cuerpo


def testEsquemaBaseDatosInicializadoAlArrancar() -> None:
    """Verifica que la persistencia relacional SQLite se inicialice y las tablas requeridas existan."""
    from app.main import obtenerConexionApp

    conexion: sqlite3.Connection = obtenerConexionApp()
    cursor = conexion.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('proyectos', 'paquetes_trabajo', 'tareas');"
    )
    tablas = {fila[0] for fila in cursor.fetchall()}

    assert {"proyectos", "paquetes_trabajo", "tareas"}.issubset(tablas)


def testSinEndpointsRestManuales() -> None:
    """Verifica que no existan endpoints REST manuales en la aplicación FastAPI (regla estricta RNF-03)."""
    from app.main import app

    rutasApi = [
        getattr(ruta, "path", "")
        for ruta in app.routes
        if getattr(ruta, "path", "").startswith("/api")
    ]
    assert rutasApi == [], "No deben exponerse endpoints REST manuales en la aplicación"


def testMontajeComponenteReactPyConfigurado() -> None:
    """Verifica que ReactPy esté montado sobre la aplicación FastAPI mediante sus rutas internas."""
    from app.main import app

    rutas = [getattr(ruta, "path", "") for ruta in app.routes]
    # ReactPy monta rutas estáticas o de websocket para sus módulos y layouts
    rutasReactPy = [r for r in rutas if "_reactpy" in r or r == "/" or "stream" in r]
    assert len(rutasReactPy) > 0, (
        "Debe existir al menos una ruta de ReactPy registrada en FastAPI"
    )
