"""Módulo de formateadores visuales para la interfaz de consola de AgilBan."""

from app.core.edt import (
    calcularAvancePaquete,
    calcularEstadoPaquete,
    obtenerTareasActivas,
)
from app.domain.catalogos import EstadoKanban
from app.domain.modelos import Integrante, Proyecto, Tarea
from app.domain.monadas import Alguno


def esTareaVencida(tarea: Tarea, fechaReferencia: str) -> bool:
    """Determina puramente si una tarea está vencida respecto a una fecha ISO de referencia."""
    if not fechaReferencia:
        return False
    if tarea.estado == EstadoKanban.TERMINADA:
        return False
    match tarea.fechaObjetivo:
        case Alguno(fecha):
            return fecha < fechaReferencia
        case _:
            return False


def obtenerNombreResponsable(
    cedulaOpcion: object, integrantes: tuple[Integrante, ...]
) -> str:
    """Busca el nombre legible de un responsable a partir de su cédula opcional."""
    match cedulaOpcion:
        case Alguno(cedula):
            for integrante in integrantes:
                if integrante.cedula == cedula:
                    return integrante.nombre
            return f"Cédula: {cedula}"
        case _:
            return "Sin asignar"


def formatearTablaProyectos(proyectos: tuple[Proyecto, ...]) -> str:
    """Genera una tabla visual de proyectos registrados en la consola."""
    if not proyectos:
        return "No hay proyectos registrados en el sistema. ¡Cree uno nuevo con el asistente!"

    lineas = [
        "=" * 85,
        f"{'PROYECTOS REGISTRADOS EN AGILBAN':^85}",
        "=" * 85,
        f"{'ID':<12} | {'NOMBRE DEL PROYECTO':<36} | {'TIPO':<22} | {'PAQ':<4} | {'INT':<4}",
        "-" * 85,
    ]

    for p in proyectos:
        lineas.append(
            f"{p.idProyecto:<12} | {p.nombre[:36]:<36} | {p.tipo.value[:22]:<22} | "
            f"{len(p.paquetes):<4} | {len(p.integrantes):<4}"
        )

    lineas.append("=" * 85)
    return "\n".join(lineas)


def formatearTablaIntegrantes(integrantes: tuple[Integrante, ...]) -> str:
    """Genera una tabla de integrantes pertenecientes al proyecto."""
    if not integrantes:
        return "No hay integrantes registrados en este proyecto."

    lineas = [
        "-" * 75,
        f"{'CÉDULA':<14} | {'NOMBRE Y APELLIDO':<32} | {'CARGO':<24}",
        "-" * 75,
    ]

    for i in integrantes:
        lineas.append(
            f"{i.cedula:<14} | {i.nombre[:32]:<32} | {i.cargo.value[:24]:<24}"
        )

    lineas.append("-" * 75)
    return "\n".join(lineas)


def formatearTablaEDT(proyecto: Proyecto, fechaReferencia: str = "") -> str:
    """Genera una representación jerárquica de la EDT del proyecto con sus paquetes y tareas."""
    if not proyecto.paquetes:
        return "El proyecto no cuenta con paquetes de trabajo en la EDT."

    lineas = [
        "=" * 92,
        f"EDT (ESTRUCTURA DE DESGLOSE DEL TRABAJO) — PROYECTO: {proyecto.nombre}",
        "=" * 92,
    ]

    for paquete in proyecto.paquetes:
        estadoPaq = calcularEstadoPaquete(paquete).value
        avancePaq = calcularAvancePaquete(paquete)
        lineas.append(f"\n📦 PAQUETE: [{paquete.idPaquete}] {paquete.nombre}")
        lineas.append(
            f"   Estado derivado: {estadoPaq} | Avance completado: {avancePaq:.1f}%"
        )

        tareasActivas = obtenerTareasActivas(paquete)
        if not tareasActivas:
            lineas.append("   └─ (Sin tareas activas asignadas a este paquete)")
        else:
            lineas.append(
                f"   {'ID':<10} | {'TÍTULO':<30} | {'ESTADO':<14} | {'PRIORIDAD':<10} | {'RESPONSABLE':<18}"
            )
            lineas.append("   " + "-" * 88)
            for t in tareasActivas:
                vencidaBadge = (
                    " [Vencida]" if esTareaVencida(t, fechaReferencia) else ""
                )
                respNom = obtenerNombreResponsable(
                    t.cedulaResponsable, proyecto.integrantes
                )
                lineas.append(
                    f"   {t.idTarea:<10} | {t.titulo[:28] + vencidaBadge:<30} | "
                    f"{t.estado.value:<14} | {t.prioridad.value:<10} | {respNom[:18]:<18}"
                )

    lineas.append("\n" + "=" * 92)
    return "\n".join(lineas)


def formatearTableroKanban(
    tareas: tuple[Tarea, ...],
    integrantes: tuple[Integrante, ...] = (),
    fechaReferencia: str = "",
) -> str:
    """Genera el tablero Kanban limpio de 4 columnas delimitadas visualmente."""
    columnas = {
        EstadoKanban.PENDIENTE: [
            t for t in tareas if t.estado == EstadoKanban.PENDIENTE
        ],
        EstadoKanban.EN_PROGRESO: [
            t for t in tareas if t.estado == EstadoKanban.EN_PROGRESO
        ],
        EstadoKanban.EN_REVISION: [
            t for t in tareas if t.estado == EstadoKanban.EN_REVISION
        ],
        EstadoKanban.TERMINADA: [
            t for t in tareas if t.estado == EstadoKanban.TERMINADA
        ],
    }

    anchoCol = 28
    separador = "+" + ("-" * anchoCol + "+") * 4

    lineas = [
        "=" * (anchoCol * 4 + 5),
        f"{'TABLERO KANBAN OPERATIVO':^{anchoCol * 4 + 5}}",
        "=" * (anchoCol * 4 + 5),
        separador,
        (
            f"| {'1. ' + EstadoKanban.PENDIENTE.value + ' (' + str(len(columnas[EstadoKanban.PENDIENTE])) + ')':<{anchoCol - 2}} "
            f"| {'2. ' + EstadoKanban.EN_PROGRESO.value + ' (' + str(len(columnas[EstadoKanban.EN_PROGRESO])) + ')':<{anchoCol - 2}} "
            f"| {'3. ' + EstadoKanban.EN_REVISION.value + ' (' + str(len(columnas[EstadoKanban.EN_REVISION])) + ')':<{anchoCol - 2}} "
            f"| {'4. ' + EstadoKanban.TERMINADA.value + ' (' + str(len(columnas[EstadoKanban.TERMINADA])) + ')':<{anchoCol - 2}} |"
        ),
        separador,
    ]

    maxFilas = max((len(cols) for cols in columnas.values()), default=0)
    if maxFilas == 0:
        lineas.append(
            f"| {'(Sin tareas)':<{anchoCol - 2}} | {'(Sin tareas)':<{anchoCol - 2}} | "
            f"{'(Sin tareas)':<{anchoCol - 2}} | {'(Sin tareas)':<{anchoCol - 2}} |"
        )
        lineas.append(separador)
    else:
        estados = (
            EstadoKanban.PENDIENTE,
            EstadoKanban.EN_PROGRESO,
            EstadoKanban.EN_REVISION,
            EstadoKanban.TERMINADA,
        )
        for i in range(maxFilas):
            filaTitulo = []
            filaDetalle = []
            filaBadges = []

            for estado in estados:
                lista = columnas[estado]
                if i < len(lista):
                    t = lista[i]
                    resp = obtenerNombreResponsable(t.cedulaResponsable, integrantes)
                    filaTitulo.append(f"[{t.idTarea}] {t.titulo}"[: anchoCol - 2])
                    filaDetalle.append(f"{t.prioridad.value} | {resp}"[: anchoCol - 2])

                    etiquetas = []
                    if t.contadorRegresos > 0:
                        etiquetas.append(f"Regresos: {t.contadorRegresos}")
                    if esTareaVencida(t, fechaReferencia):
                        etiquetas.append("Vencida")
                    filaBadges.append(
                        f"[{' | '.join(etiquetas)}]"[: anchoCol - 2]
                        if etiquetas
                        else ""
                    )
                else:
                    filaTitulo.append("")
                    filaDetalle.append("")
                    filaBadges.append("")

            lineas.append(
                f"| {filaTitulo[0]:<{anchoCol - 2}} | {filaTitulo[1]:<{anchoCol - 2}} | "
                f"{filaTitulo[2]:<{anchoCol - 2}} | {filaTitulo[3]:<{anchoCol - 2}} |"
            )
            lineas.append(
                f"| {filaDetalle[0]:<{anchoCol - 2}} | {filaDetalle[1]:<{anchoCol - 2}} | "
                f"{filaDetalle[2]:<{anchoCol - 2}} | {filaDetalle[3]:<{anchoCol - 2}} |"
            )
            lineas.append(
                f"| {filaBadges[0]:<{anchoCol - 2}} | {filaBadges[1]:<{anchoCol - 2}} | "
                f"{filaBadges[2]:<{anchoCol - 2}} | {filaBadges[3]:<{anchoCol - 2}} |"
            )
            lineas.append(separador)

    return "\n".join(lineas)


def formatearPanelMetricas(
    resumen: dict[str, int],
    avanceGlobal: float,
    carga: dict[str, dict[str, int]],
    cuellos: tuple[Tarea, ...],
    integrantes: tuple[Integrante, ...] = (),
) -> str:
    """Genera el panel cuantitativo y analítico con métricas y auditoría de cuellos de botella."""
    lineas = [
        "=" * 85,
        f"{'PANEL DE MÉTRICAS Y ANALÍTICA DEL PROYECTO':^85}",
        "=" * 85,
        "\n1. RESUMEN GLOBAL DE TAREAS:",
        f"   - Tareas Activas:    {resumen.get('activas', 0)}",
        f"   - Tareas Inactivas:  {resumen.get('inactivas', 0)} (descartadas lógicamente)",
        f"   - En Pendiente:      {resumen.get(EstadoKanban.PENDIENTE.value, 0)}",
        f"   - En Progreso:       {resumen.get(EstadoKanban.EN_PROGRESO.value, 0)}",
        f"   - En Revisión:       {resumen.get(EstadoKanban.EN_REVISION.value, 0)}",
        f"   - Terminadas:        {resumen.get(EstadoKanban.TERMINADA.value, 0)}",
    ]

    if resumen.get("activas", 0) == 0:
        lineas.append("   - Avance Global:     0.0% (Sin tareas registradas)")
    else:
        lineas.append(f"   - Avance Global:     {avanceGlobal:.1f}%")

    lineas.append("\n2. DISTRIBUCIÓN DE CARGA POR INTEGRANTE:")
    lineas.append(f"   {'INTEGRANTE':<36} | {'ASIGNADAS':<10} | {'TERMINADAS':<10}")
    lineas.append("   " + "-" * 62)
    for cedula, datos in carga.items():
        nombre = cedula
        for integ in integrantes:
            if integ.cedula == cedula:
                nombre = f"{integ.nombre} ({cedula})"
                break
        lineas.append(
            f"   {nombre[:36]:<36} | {datos.get('asignadas', 0):<10} | {datos.get('terminadas', 0):<10}"
        )

    lineas.append("\n3. AUDITORÍA DE CUELLOS DE BOTELLA (TAREAS CON REGRESOS):")
    if not cuellos:
        lineas.append(
            "   (No se registran tareas con devoluciones o cuellos de botella)"
        )
    else:
        for c in cuellos:
            lineas.append(
                f"   ⚠️  [{c.idTarea}] {c.titulo} — Regresos acumulados: {c.contadorRegresos}"
            )
            lineas.append("      Historial de justificaciones:")
            justificaciones = [
                h.comentario.valor
                for h in c.historial
                if isinstance(h.comentario, Alguno) and h.comentario.valor
            ]
            if justificaciones:
                for j in justificaciones:
                    lineas.append(f'      • "{j}"')
            else:
                lineas.append("      • (Sin comentarios registrados)")

    lineas.append("\n" + "=" * 85)
    return "\n".join(lineas)


def formatearListaTareas(
    tareas: tuple[Tarea, ...],
    integrantes: tuple[Integrante, ...] = (),
    fechaReferencia: str = "",
) -> str:
    """Genera la lista formateada para la sección de consultas analíticas y filtros."""
    if not tareas:
        return "No se encontraron tareas que coincidan con los criterios de filtro seleccionados."

    lineas = [
        "-" * 105,
        f"{'ID':<10} | {'TÍTULO':<28} | {'ESTADO':<14} | {'PRIORIDAD':<10} | {'RESPONSABLE':<18} | {'VENCE':<11} | {'REG':<3}",
        "-" * 105,
    ]

    for t in tareas:
        vencidaBadge = " [!]" if esTareaVencida(t, fechaReferencia) else ""
        respNom = obtenerNombreResponsable(t.cedulaResponsable, integrantes)
        fechaStr = (
            t.fechaObjetivo.valor if isinstance(t.fechaObjetivo, Alguno) else "N/A"
        )
        lineas.append(
            f"{t.idTarea:<10} | {t.titulo[:24] + vencidaBadge:<28} | {t.estado.value:<14} | "
            f"{t.prioridad.value:<10} | {respNom[:18]:<18} | {fechaStr:<11} | {t.contadorRegresos:<3}"
        )

    lineas.append("-" * 105)
    return "\n".join(lineas)
