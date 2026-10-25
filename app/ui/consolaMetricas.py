# ruff: noqa: N999
"""Módulo de consulta analítica, métricas, cuellos de botella y filtrado en consola.

Centraliza las consultas cuantitativas del proyecto, auditoría de devoluciones
y búsqueda combinable de tareas sin sobrecargar la vista operativa del Kanban.
"""

from __future__ import annotations

import datetime
import sqlite3
from collections.abc import Callable

from app.adapters.repositorioSqlite import recuperarProyectos
from app.core.edt import (
    calcularAvancePaquete,
    calcularEstadoPaquete,
)
from app.core.filtros import (
    crearCriterioFiltro,
    filtrarTareas,
    ordenarPorFecha,
    ordenarPorPrioridad,
)
from app.core.metricas import (
    auditarCuellosDeBotella,
    calcularAvanceGlobal,
    calcularCargaIntegrantes,
    calcularResumenTareas,
)
from app.domain.catalogos import EstadoKanban, PrioridadTarea
from app.domain.modelos import Proyecto, Tarea
from app.domain.monadas import Alguno, Exito, Ninguno, Opcion
from app.ui.formateadores import (
    formatearListaTareas,
    formatearPanelMetricas,
    obtenerNombreResponsable,
)


def buscarProyectoPorId(
    conexion: sqlite3.Connection, idProyecto: str
) -> Proyecto | None:
    """Recupera la versión actualizada del proyecto desde la base de datos."""
    res = recuperarProyectos(conexion)
    if isinstance(res, Exito):
        for p in res.valor:
            if p.idProyecto == idProyecto:
                return p
    return None


def obtenerTodasLasTareas(proyecto: Proyecto) -> tuple[Tarea, ...]:
    """Retorna todas las tareas del proyecto recorriendo de forma pura sus paquetes de trabajo."""
    return tuple(t for paq in proyecto.paquetes for t in paq.tareas)


def mostrarPanelGeneralMetricas(
    proyecto: Proyecto,
    emisor: Callable[[str], None],
) -> None:
    """Calcula y despliega las métricas consolidadas, avance por paquete y distribución de carga."""
    todasTareas = obtenerTodasLasTareas(proyecto)
    resumen = calcularResumenTareas(todasTareas)
    # Compatibilidad de claves con el formateador
    resumen["activas"] = resumen.get("totalActivas", 0)
    resumen["inactivas"] = resumen.get("totalInactivas", 0)

    avanceGlobal = calcularAvanceGlobal(todasTareas)
    carga = calcularCargaIntegrantes(proyecto.integrantes, todasTareas)
    cuellos = auditarCuellosDeBotella(todasTareas)

    emisor(
        "\n"
        + formatearPanelMetricas(
            resumen, avanceGlobal, carga, cuellos, proyecto.integrantes
        )
    )

    # Avance desglosado por paquete de trabajo
    emisor("\n4. AVANCE DETALLADO POR PAQUETE DE TRABAJO (EDT):")
    if not proyecto.paquetes:
        emisor("   (No hay paquetes registrados en la EDT)")
    else:
        for paq in proyecto.paquetes:
            estadoDerivado = calcularEstadoPaquete(paq).value
            avancePaq = calcularAvancePaquete(paq)
            activasPaq = sum(1 for t in paq.tareas if t.activo)
            emisor(
                f"   • [{paq.idPaquete}] {paq.nombre:<32} | Estado: {estadoDerivado:<12} | "
                f"Avance: {avancePaq:5.1f}% ({activasPaq} tareas activas)"
            )
    emisor("=" * 85)


def mostrarAuditoriaCuellosDeBotella(
    proyecto: Proyecto,
    emisor: Callable[[str], None],
) -> None:
    """Presenta el informe detallado de tareas con retrocesos acumulados e historial de motivos."""
    todasTareas = obtenerTodasLasTareas(proyecto)
    cuellos = auditarCuellosDeBotella(todasTareas)

    emisor("\n" + "=" * 80)
    emisor(f"{'AUDITORÍA DE CUELLOS DE BOTELLA Y DEVOLUCIONES':^80}")
    emisor("=" * 80)

    if not cuellos:
        emisor(
            "\n✅ ¡Excelente! No existen tareas con devoluciones o regresos acumulados."
        )
        emisor("=" * 80)
        return

    emisor(
        f"\nSe detectaron {len(cuellos)} tarea(s) con regresos en el flujo de trabajo:\n"
    )
    for idx, c in enumerate(cuellos, 1):
        resp = obtenerNombreResponsable(c.cedulaResponsable, proyecto.integrantes)
        emisor(f"{idx}. ⚠️  [{c.idTarea}] {c.titulo}")
        emisor(
            f"   Estado actual: {c.estado.value} | Prioridad: {c.prioridad.value} | Responsable: {resp}"
        )
        emisor(f"   Total de devoluciones acumuladas: {c.contadorRegresos}")
        emisor("   Historial cronológico de justificaciones:")

        justificaciones = [
            h
            for h in c.historial
            if isinstance(h.comentario, Alguno) and h.comentario.valor
        ]
        if justificaciones:
            for j in justificaciones:
                emisor(
                    f'     • [{j.fechaHora}] {j.estadoOrigen.value} ➔ {j.estadoDestino.value}: "{j.comentario.valor}"'
                )
        else:
            emisor("     • (Sin justificaciones registradas)")
        emisor("-" * 80)
    emisor("=" * 80)


def configurarFiltroInteractivo(
    proyecto: Proyecto,
    lector: Callable[[str], str],
    emisor: Callable[[str], None],
) -> None:
    """Permite seleccionar criterios de filtrado y ordenamiento analítico."""
    todasTareas = obtenerTodasLasTareas(proyecto)
    if not todasTareas:
        emisor("\n⚠️  No hay tareas registradas en este proyecto.")
        return

    emisor("\n--- Configuración de Consulta Analítica y Filtros ---")

    # 1. Filtro por Estado Kanban
    emisor("\n1. Filtrar por Estado Kanban:")
    emisor("  0. Todos los estados")
    estados = list(EstadoKanban)
    for idx, e in enumerate(estados, 1):
        emisor(f"  {idx}. {e.value}")
    selEstado = lector("Seleccione estado (por defecto 0): ").strip()
    filtroEstado: Opcion[EstadoKanban] = Ninguno()
    if selEstado.isdigit() and 1 <= int(selEstado) <= len(estados):
        filtroEstado = Alguno(estados[int(selEstado) - 1])

    # 2. Filtro por Responsable
    emisor("\n2. Filtrar por Integrante Responsable:")
    emisor("  0. Todos los integrantes")
    for idx, integ in enumerate(proyecto.integrantes, 1):
        emisor(f"  {idx}. {integ.nombre} ({integ.cedula})")
    selResp = lector("Seleccione integrante (por defecto 0): ").strip()
    filtroCedula: Opcion[str] = Ninguno()
    if selResp.isdigit() and 1 <= int(selResp) <= len(proyecto.integrantes):
        filtroCedula = Alguno(proyecto.integrantes[int(selResp) - 1].cedula)

    # 3. Filtro por Prioridad
    emisor("\n3. Filtrar por Nivel de Prioridad:")
    emisor("  0. Todas las prioridades")
    prioridades = list(PrioridadTarea)
    for idx, p in enumerate(prioridades, 1):
        emisor(f"  {idx}. {p.value}")
    selPrio = lector("Seleccione prioridad (por defecto 0): ").strip()
    filtroPrio: Opcion[PrioridadTarea] = Ninguno()
    if selPrio.isdigit() and 1 <= int(selPrio) <= len(prioridades):
        filtroPrio = Alguno(prioridades[int(selPrio) - 1])

    # 4. Solo Vencidas
    selVencidas = (
        lector("\n¿Filtrar únicamente tareas vencidas? (S/N) [por defecto N]: ")
        .strip()
        .upper()
    )
    soloVencidas = selVencidas == "S"

    # 5. Solo Inactivas (Descartadas lógicamente)
    selInactivas = (
        lector(
            "¿Filtrar únicamente tareas descartadas (inactivas)? (S/N) [por defecto N]: "
        )
        .strip()
        .upper()
    )
    soloInactivas = selInactivas == "S"

    # Aplicar predicado funcional con closure y HOF
    fechaHoy = datetime.date.today().isoformat()
    criterio = crearCriterioFiltro(
        estado=filtroEstado,
        cedula=filtroCedula,
        prioridad=filtroPrio,
        soloVencidas=soloVencidas,
        soloInactivas=soloInactivas,
        fechaReferencia=fechaHoy,
    )
    tareasFiltradas = filtrarTareas(todasTareas, criterio)

    # Ordenamiento
    emisor("\nOpciones de Ordenamiento de Resultados:")
    emisor("  1. Por fecha objetivo cronológica ascendente")
    emisor("  2. Por nivel de prioridad (Crítica > Alta > Media > Baja)")
    emisor("  0. Sin ordenamiento específico")
    selOrden = lector("Seleccione ordenamiento (por defecto 0): ").strip()

    match selOrden:
        case "1":
            tareasOrdenadas = ordenarPorFecha(tareasFiltradas)
        case "2":
            tareasOrdenadas = ordenarPorPrioridad(tareasFiltradas)
        case _:
            tareasOrdenadas = tareasFiltradas

    # Presentación final
    emisor(
        f"\nResultados de la Consulta ({len(tareasOrdenadas)} tarea(s) encontrada(s)):"
    )
    emisor(formatearListaTareas(tareasOrdenadas, proyecto.integrantes, fechaHoy))


def ejecutarMenuMetricas(
    conexion: sqlite3.Connection,
    idProyecto: str,
    lector: Callable[[str], str] = input,
    emisor: Callable[[str], None] = print,
) -> None:
    """Controla el menú interactivo para consultas analíticas, avance y cuellos de botella."""
    while True:
        proyecto = buscarProyectoPorId(conexion, idProyecto)
        if not proyecto:
            emisor("❌ Error: Proyecto no encontrado en base de datos.")
            break

        emisor("\n" + "=" * 65)
        emisor(f"   SECCIÓN ANALÍTICA Y MÉTRICAS — {proyecto.nombre.upper()}")
        emisor("=" * 65)
        emisor("1. Ver panel consolidado de métricas y avance de la EDT")
        emisor("2. Auditar cuellos de botella (Tareas con regresos)")
        emisor("3. Consulta analítica y filtrado interactivo de tareas")
        emisor("0. Volver al Menú del Proyecto")

        opcion = lector("\nSeleccione una opción: ").strip()

        match opcion:
            case "1":
                mostrarPanelGeneralMetricas(proyecto, emisor)
            case "2":
                mostrarAuditoriaCuellosDeBotella(proyecto, emisor)
            case "3":
                configurarFiltroInteractivo(proyecto, lector, emisor)
            case "0":
                break
            case _:
                emisor("⚠️  Opción no válida. Por favor, ingrese un número del 0 al 3.")
