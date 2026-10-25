"""Módulo principal de consola REPL y navegación de usuario para AgilBan."""

import sqlite3
from collections.abc import Callable

from app.adapters.repositorioSqlite import guardarProyectoCompleto, recuperarProyectos
from app.domain.modelos import Proyecto
from app.domain.monadas import Exito, Fallo
from app.ui.asistenteProyecto import ejecutarAsistenteCreacionProyecto
from app.ui.formateadores import formatearTablaProyectos


def buscarProyectoPorId(
    proyectos: tuple[Proyecto, ...], idProyecto: str
) -> Proyecto | None:
    """Encuentra un proyecto por su identificador único dentro de la tupla."""
    for p in proyectos:
        if p.idProyecto == idProyecto:
            return p
    return None


def ejecutarMenuProyecto(
    conexion: sqlite3.Connection,
    idProyecto: str,
    lector: Callable[[str], str] = input,
    emisor: Callable[[str], None] = print,
) -> None:
    """Controla el submenú operativo del proyecto activo seleccionado."""
    while True:
        resProyectos = recuperarProyectos(conexion)
        if isinstance(resProyectos, Fallo):
            emisor(f"❌ Error al consultar base de datos: {resProyectos.error}")
            break

        proyecto = buscarProyectoPorId(resProyectos.valor, idProyecto)
        if proyecto is None:
            emisor("❌ El proyecto ya no se encuentra en el sistema.")
            break

        emisor("\n" + "=" * 70)
        emisor(f"  PROYECTO ACTIVO: {proyecto.nombre.upper()} [{proyecto.idProyecto}]")
        emisor(
            f"  Tipo: {proyecto.tipo.value} | Paquetes: {len(proyecto.paquetes)} | Equipo: {len(proyecto.integrantes)}"
        )
        emisor("=" * 70)
        emisor("1. Gestionar EDT (Paquetes e Integrantes)")
        emisor("2. Ver y Operar Tablero Kanban")
        emisor("3. Consultar Métricas y Filtros Analíticos")
        emisor("0. Volver al Menú Principal")

        opcion = lector("\nSeleccione una opción: ").strip()

        match opcion:
            case "1":
                try:
                    from app.ui.consolaEdt import ejecutarMenuEdt

                    ejecutarMenuEdt(conexion, proyecto.idProyecto, lector, emisor)
                except ImportError:
                    emisor("\n(Módulo de Gestión de EDT en preparación)")
            case "2":
                try:
                    from app.ui.consolaKanban import ejecutarMenuKanban

                    ejecutarMenuKanban(conexion, proyecto.idProyecto, lector, emisor)
                except ImportError:
                    emisor("\n(Módulo de Tablero Kanban en preparación)")
            case "3":
                try:
                    from app.ui.consolaMetricas import ejecutarMenuMetricas

                    ejecutarMenuMetricas(conexion, proyecto.idProyecto, lector, emisor)
                except ImportError:
                    emisor("\n(Módulo de Métricas y Analítica en preparación)")
            case "0":
                emisor("\nRegresando al menú principal...")
                break
            case _:
                emisor(
                    "⚠️  Opción no reconocida. Por favor, ingrese un número válido de la lista."
                )


def ejecutarMenuPrincipal(
    conexion: sqlite3.Connection,
    lector: Callable[[str], str] = input,
    emisor: Callable[[str], None] = print,
) -> None:
    """Controla el bucle REPL de nivel superior de la aplicación."""
    emisor("\n" + "#" * 60)
    emisor("###       BIENVENIDO A AGILBAN — GESTIÓN ÁGIL LOCAL       ###")
    emisor("#" * 60)

    while True:
        resProyectos = recuperarProyectos(conexion)
        proyectos = resProyectos.valor if isinstance(resProyectos, Exito) else ()

        emisor("\n" + "-" * 50)
        emisor("             MENÚ PRINCIPAL AGILBAN")
        emisor("-" * 50)
        emisor("1. Ver proyectos registrados")
        emisor("2. Seleccionar proyecto activo")
        emisor("3. Crear nuevo proyecto (Asistente guiado)")
        emisor("0. Salir de la aplicación")

        opcion = lector("\nSeleccione una opción: ").strip()

        match opcion:
            case "1":
                emisor("\n" + formatearTablaProyectos(proyectos))

            case "2":
                if not proyectos:
                    emisor(
                        "\n⚠️  No hay proyectos registrados aún. Debe crear uno primero (Opción 3)."
                    )
                    continue

                emisor("\nSeleccione un proyecto de la lista:")
                for idx, p in enumerate(proyectos, 1):
                    emisor(f"  {idx}. [{p.idProyecto}] {p.nombre} ({p.tipo.value})")

                seleccion = lector(
                    "\nIngrese el número del proyecto (o '0' para cancelar): "
                ).strip()
                if seleccion == "0" or seleccion.lower() == "cancelar":
                    continue
                if seleccion.isdigit() and 1 <= int(seleccion) <= len(proyectos):
                    proyElegido = proyectos[int(seleccion) - 1]
                    ejecutarMenuProyecto(
                        conexion, proyElegido.idProyecto, lector, emisor
                    )
                else:
                    emisor(
                        "⚠️  Selección inválida. Ingrese un número de proyecto válido."
                    )

            case "3":
                nombresExistentes = tuple(p.nombre for p in proyectos)
                resNuevo = ejecutarAsistenteCreacionProyecto(
                    nombresExistentes=nombresExistentes,
                    lector=lector,
                    emisor=emisor,
                )
                match resNuevo:
                    case Exito(nuevoProyecto):
                        resGuardar = guardarProyectoCompleto(conexion, nuevoProyecto)
                        match resGuardar:
                            case Exito(_):
                                emisor(
                                    f"\n🎉 ¡Proyecto '{nuevoProyecto.nombre}' guardado exitosamente en base de datos!"
                                )
                            case Fallo(err):
                                emisor(f"\n❌ Error al guardar el proyecto: {err}")
                    case Fallo(mensaje):
                        emisor(f"\nℹ️  {mensaje}")

            case "0":
                emisor("\nSaliendo de AgilBan. ¡Hasta luego!")
                break

            case _:
                emisor(
                    "⚠️  Opción no reconocida. Por favor, ingrese un número válido del menú."
                )
