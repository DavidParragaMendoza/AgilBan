"""Componente raíz y contenedor SPA para la aplicación web AgilBan en ReactPy.

Gestiona el punto de montaje central del árbol de componentes reactivos.
"""

from __future__ import annotations

import sqlite3

from reactpy import component, html


@component
def componenteApp(conexion: sqlite3.Connection | None = None):
    """Componente raíz montado en el servidor web.

    Actúa como el contenedor principal de la Single Page Application (SPA).
    """
    return html.div(
        {
            "id": "agilban-contenedor-raiz",
            "className": "min-h-screen bg-slate-50 text-slate-900 font-sans antialiased flex flex-col",
        },
        html.header(
            {
                "className": "bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between shadow-sm"
            },
            html.div(
                {"className": "flex items-center space-x-3"},
                html.div(
                    {
                        "className": "w-8 h-8 rounded bg-indigo-600 flex items-center justify-center text-white font-bold text-sm shadow"
                    },
                    "AB",
                ),
                html.span(
                    {
                        "className": "text-lg font-semibold tracking-tight text-slate-800"
                    },
                    "AgilBan",
                ),
                html.span(
                    {
                        "className": "text-xs font-medium px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100"
                    },
                    "Fase 2 — GUI Web",
                ),
            ),
        ),
        html.main(
            {
                "className": "flex-1 flex flex-col items-center justify-center p-6 text-center"
            },
            html.div(
                {
                    "className": "max-w-md w-full bg-white p-8 rounded-xl shadow-sm border border-slate-200 space-y-4"
                },
                html.h1(
                    {"className": "text-2xl font-bold text-slate-800 tracking-tight"},
                    "Gestión Ágil Local de Proyectos",
                ),
                html.p(
                    {"className": "text-sm text-slate-600 leading-relaxed"},
                    "Servidor FastAPI y canal reactivo ReactPy inicializados correctamente con Tailwind CSS.",
                ),
            ),
        ),
    )
