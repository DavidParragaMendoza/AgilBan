# ruff: noqa: N999
"""Módulo de navegación y operación interactiva del Tablero Kanban en consola."""

import datetime
import sqlite3
import uuid
from collections.abc import Callable

from app.adapters.repositorioSqlite import (
    crearTareaConHistorial,
    guardarTareaConHistorial,
    recuperarProyectos,
)
from app.core.edt import obtenerTareasActivas
from app.core.kanban import (
    avanzarOTareasKanban,
    destinoRetroceso,
    esRetroceso,
    transicionesPermitidas,
)
from app.core.validador import validarDatosTarea
from app.domain.catalogos import PrioridadTarea
from app.domain.modelos import (
    Integrante,
    PaqueteTrabajo,
    Proyecto,
    Tarea,
)
from app.domain.monadas import Alguno, Exito, Fallo, Ninguno
from app.ui.formateadores import formatearTableroKanban, obtenerNombreResponsable


def obtenerMarcaTiempoActual() -> str:
    """Retorna la marca temporal actual en formato ISO 8601."""
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def seleccionarPrioridad(
    lector: Callable[[str], str], emisor: Callable[[str], None]
) -> PrioridadTarea:
    """Solicita la selección de prioridad de una tarea del catálogo predefinido."""
    prioridades = list(PrioridadTarea)
    while True:
        emisor("\nSeleccione la prioridad de la tarea:")
        for idx, prio in enumerate(prioridades, 1):
            emisor(f"  {idx}. {prio.value}")
        entrada = lector("Número de prioridad (por defecto 2. Media): ").strip()
        if not entrada or entrada == "0" or entrada.lower() == "cancelar":
            return PrioridadTarea.MEDIA
        if entrada.isdigit() and 1 <= int(entrada) <= len(prioridades):
            return prioridades[int(entrada) - 1]
        emisor("⚠️  Opción no reconocida. Ingrese un número válido de la lista.")


def seleccionarResponsable(
    integrantes: tuple[Integrante, ...],
    lector: Callable[[str], str],
    emisor: Callable[[str], None],
) -> Alguno[str] | Ninguno:
    """Permite seleccionar un integrante como responsable o dejarlo 'Sin asignar'."""
    if not integrantes:
        return Ninguno()

    while True:
        emisor("\nAsignar responsable de la tarea:")
        emisor("  0. Sin asignar")
        for idx, integ in enumerate(integrantes, 1):
            emisor(f"  {idx}. {integ.nombre} (Cédula: {integ.cedula})")
        entrada = lector("Seleccione el responsable: ").strip()
        if entrada == "0" or not entrada:
            return Ninguno()
        if entrada.isdigit() and 1 <= int(entrada) <= len(integrantes):
            return Alguno(integrantes[int(entrada) - 1].cedula)
        emisor("⚠️  Opción no reconocida. Ingrese un número válido de la lista.")


def registrarAltaRapidaTarea(
    conexion: sqlite3.Connection,
    paquete: PaqueteTrabajo,
    proyecto: Proyecto,
    lector: Callable[[str], str],
    emisor: Callable[[str], None],
) -> None:
    """Guía la creación y persistencia inmediata de una nueva tarea en el paquete."""
    emisor("\n--- Alta Rápida de Nueva Tarea ---")

    # 1. Título
    titulo = ""
    while True:
        titulo = lector("Título de la tarea: ").strip()
        if not titulo:
            emisor("⚠️  El título de la tarea no puede estar vacío.")
            continue
        if len(titulo) > 120:
            emisor("⚠️  El título no puede exceder los 120 caracteres.")
            continue
        break

    # 2. Prioridad
    prioridad = seleccionarPrioridad(lector, emisor)

    # 3. Descripción opcional
    entradaDesc = lector(
        "Descripción detallada (opcional, presione Enter para omitir): "
    ).strip()
    descripcion = Alguno(entradaDesc) if entradaDesc else Ninguno()

    # 4. Responsable opcional
    responsable = seleccionarResponsable(proyecto.integrantes, lector, emisor)

    # 5. Fecha objetivo opcional
    fechaObjetivo: Alguno[str] | Ninguno = Ninguno()
    while True:
        entradaFecha = lector(
            "Fecha objetivo AAAA-MM-DD (opcional, presione Enter para omitir): "
        ).strip()
        if not entradaFecha:
            break
        valRes = validarDatosTarea(titulo, descripcion, Alguno(entradaFecha))
        match valRes:
            case Exito(_):
                fechaObjetivo = Alguno(entradaFecha)
                break
            case Fallo(err):
                emisor(f"⚠️  {err.mensaje}")

    # Validar datos consolidados
    valFinal = validarDatosTarea(titulo, descripcion, fechaObjetivo)
    match valFinal:
        case Fallo(err):
            emisor(f"❌ Error al validar tarea: {err.mensaje}")
            return
        case Exito(_):
            pass

    resCrear = crearTareaConHistorial(
        conexion=conexion,
        idPaquete=paquete.idPaquete,
        titulo=titulo,
        descripcion=descripcion,
        prioridad=prioridad,
        cedulaResponsable=responsable,
        fechaObjetivo=fechaObjetivo,
        timestamp=obtenerMarcaTiempoActual(),
        claveSolicitud=uuid.uuid4().hex,
    )
    match resCrear:
        case Exito(tareaCreada):
            emisor(
                f"\n🎉 ¡Tarea [{tareaCreada.idTarea}] '{tareaCreada.titulo}' guardada exitosamente en el paquete!"
            )
        case Fallo(err):
            emisor(f"❌ Error al guardar la tarea en base de datos: {err}")


def moverEstadoTarea(
    conexion: sqlite3.Connection,
    tareasActivas: tuple[Tarea, ...],
    lector: Callable[[str], str],
    emisor: Callable[[str], None],
) -> None:
    """Permite seleccionar una tarea y avanzar o retroceder su estado Kanban."""
    if not tareasActivas:
        emisor("\n⚠️  No hay tareas activas disponibles para mover en este paquete.")
        return

    emisor("\nSeleccione la tarea que desea mover:")
    for idx, t in enumerate(tareasActivas, 1):
        emisor(f"  {idx}. [{t.idTarea}] {t.titulo} (Estado: {t.estado.value})")

    selTarea = lector("\nNúmero de tarea (o '0' para cancelar): ").strip()
    if (
        selTarea == "0"
        or not selTarea.isdigit()
        or not (1 <= int(selTarea) <= len(tareasActivas))
    ):
        return

    tarea = tareasActivas[int(selTarea) - 1]
    transiciones = transicionesPermitidas(tarea.estado)
    if not transiciones:
        emisor(
            f"\n⚠️  La tarea en estado '{tarea.estado.value}' no tiene transiciones permitidas."
        )
        return

    avances = tuple(
        destino for destino in transiciones if not esRetroceso(tarea.estado, destino)
    )
    destinoDevolucion = destinoRetroceso(tarea.estado)

    emisor(f"\nAcciones permitidas desde '{tarea.estado.value}':")
    for idx, destino in enumerate(avances, 1):
        emisor(f"  {idx}. Avanzar a '{destino.value}'")

    opcionDevolucion: Alguno[int] | Ninguno = Ninguno()
    match destinoDevolucion:
        case Alguno(destino):
            emisor(f"El destino automático de devolución es '{destino.value}'.")
            opcionDevolucion = Alguno(len(avances) + 1)
            emisor(f"  {opcionDevolucion.valor}. Devolver automáticamente")
        case Ninguno():
            pass

    selDestino = lector("\nSeleccione la acción (o '0' para cancelar): ").strip()
    if (
        selDestino == "0"
        or not selDestino.isdigit()
        or not (
            1
            <= int(selDestino)
            <= len(avances) + (1 if opcionDevolucion.esAlguno() else 0)
        )
    ):
        return

    seleccion = int(selDestino)
    match (opcionDevolucion, destinoDevolucion):
        case (Alguno(indice), Alguno(destino)) if seleccion == indice:
            nuevoEstado = destino
            retroceso = True
        case _:
            nuevoEstado = avances[seleccion - 1]
            retroceso = False

    comentarioOpcion: Alguno[str] | Ninguno = Ninguno()

    if retroceso:
        emisor("\n⚠️  ALERTA: Se ha detectado un RETROCESO en el flujo de trabajo.")
        emisor(
            "El comentario de justificación es OBLIGATORIO para registrar la devolución."
        )
        while True:
            justificacion = lector(
                "Ingrese el motivo / justificación de la devolución (o '0' para cancelar): "
            ).strip()
            if justificacion == "0" or justificacion.lower() == "cancelar":
                emisor("Devolución cancelada; no se modificó la tarea.")
                return
            if not justificacion:
                emisor(
                    "⚠️  El comentario de justificación para la devolución es obligatorio (máx. 300 caracteres)."
                )
                continue
            if len(justificacion) > 300:
                emisor("⚠️  El comentario no puede superar los 300 caracteres.")
                continue
            comentarioOpcion = Alguno(justificacion)
            break

    marcaTiempo = obtenerMarcaTiempoActual()
    resTransicion = avanzarOTareasKanban(
        tarea, nuevoEstado, comentarioOpcion, marcaTiempo
    )

    match resTransicion:
        case Exito(tareaActualizada):
            resGuardar = guardarTareaConHistorial(conexion, tareaActualizada)
            match resGuardar:
                case Exito(_):
                    emisor(
                        f"\n✅ Tarea [{tareaActualizada.idTarea}] actualizada con éxito a '{nuevoEstado.value}'."
                    )
                    if retroceso:
                        emisor(
                            f"   (Contador de regresos acumulados: {tareaActualizada.contadorRegresos})"
                        )
                case Fallo(err):
                    emisor(f"❌ Error al persistir la transición: {err}")
        case Fallo(err):
            emisor(f"❌ Transición rechazada: {err.mensaje}")


def verDetalleTarea(
    tarea: Tarea,
    integrantes: tuple[Integrante, ...],
    emisor: Callable[[str], None],
) -> None:
    """Muestra el detalle completo e historial inmutable de una tarea."""
    emisor("\n" + "=" * 65)
    emisor(f"DETALLE DE LA TAREA: [{tarea.idTarea}] {tarea.titulo}")
    emisor("=" * 65)
    match tarea.descripcion:
        case Alguno(desc):
            emisor(f"Descripción:     {desc}")
        case _:
            emisor("Descripción:     (Sin descripción)")
    emisor(f"Estado Kanban:   {tarea.estado.value}")
    emisor(f"Prioridad:       {tarea.prioridad.value}")
    emisor(
        f"Responsable:     {obtenerNombreResponsable(tarea.cedulaResponsable, integrantes)}"
    )
    match tarea.fechaObjetivo:
        case Alguno(f):
            emisor(f"Fecha Objetivo:  {f}")
        case _:
            emisor("Fecha Objetivo:  (Sin fecha límite)")
    emisor(f"Regresos:        {tarea.contadorRegresos}")
    emisor(f"Activa:          {'Sí' if tarea.activo else 'No (Borrada lógicamente)'}")

    emisor("\nHistorial de Transiciones:")
    for h in tarea.historial:
        comentStr = (
            f' | Motivo: "{h.comentario.valor}"'
            if isinstance(h.comentario, Alguno)
            else ""
        )
        emisor(
            f"  • [{h.fechaHora}] {h.estadoOrigen.value} ➔ {h.estadoDestino.value}{comentStr}"
        )
    emisor("=" * 65)


def operarTableroPaquete(
    conexion: sqlite3.Connection,
    idProyecto: str,
    idPaquete: str,
    lector: Callable[[str], str],
    emisor: Callable[[str], None],
) -> None:
    """Bucle interactivo del tablero Kanban para un paquete de trabajo específico."""
    while True:
        resProyectos = recuperarProyectos(conexion)
        if isinstance(resProyectos, Fallo):
            emisor(f"❌ Error al consultar proyecto: {resProyectos.error}")
            break

        proyecto = next(
            (p for p in resProyectos.valor if p.idProyecto == idProyecto), None
        )
        if not proyecto:
            emisor("❌ Proyecto no encontrado.")
            break

        paquete = next(
            (paq for paq in proyecto.paquetes if paq.idPaquete == idPaquete), None
        )
        if not paquete:
            emisor("❌ Paquete de trabajo no encontrado.")
            break

        tareasActivas = obtenerTareasActivas(paquete)
        emisor("\n" + formatearTableroKanban(tareasActivas, proyecto.integrantes))

        emisor(f"\nAcciones del Tablero [{paquete.nombre}]:")
        emisor("1. Mover / Transicionar estado de una tarea")
        emisor("2. Alta rápida de tarea en este paquete")
        emisor("3. Ver detalle e historial de una tarea")
        emisor("0. Volver a selección de paquetes")

        opcion = lector("\nSeleccione una acción: ").strip()

        match opcion:
            case "1":
                moverEstadoTarea(conexion, tareasActivas, lector, emisor)
            case "2":
                registrarAltaRapidaTarea(conexion, paquete, proyecto, lector, emisor)
            case "3":
                if not tareasActivas:
                    emisor("\n⚠️  No hay tareas activas en este paquete.")
                    continue
                emisor("\nSeleccione la tarea a consultar:")
                for idx, t in enumerate(tareasActivas, 1):
                    emisor(f"  {idx}. [{t.idTarea}] {t.titulo}")
                sel = lector("\nNúmero de tarea: ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(tareasActivas):
                    verDetalleTarea(
                        tareasActivas[int(sel) - 1], proyecto.integrantes, emisor
                    )
                else:
                    emisor("⚠️  Selección inválida.")
            case "0":
                break
            case _:
                emisor("⚠️  Opción no reconocida. Por favor, ingrese un número válido.")


def ejecutarMenuKanban(
    conexion: sqlite3.Connection,
    idProyecto: str,
    lector: Callable[[str], str] = input,
    emisor: Callable[[str], None] = print,
) -> None:
    """Permite seleccionar el paquete de trabajo a visualizar y operar en el tablero Kanban."""
    while True:
        resProyectos = recuperarProyectos(conexion)
        if isinstance(resProyectos, Fallo):
            emisor(f"❌ Error al consultar proyecto: {resProyectos.error}")
            break

        proyecto = next(
            (p for p in resProyectos.valor if p.idProyecto == idProyecto), None
        )
        if not proyecto:
            emisor("❌ Proyecto no encontrado.")
            break

        if not proyecto.paquetes:
            emisor(
                "\n⚠️  El proyecto no tiene paquetes de trabajo. Cree uno primero en la gestión de EDT."
            )
            break

        emisor("\n" + "=" * 60)
        emisor("         SELECCIÓN DE PAQUETE PARA TABLERO KANBAN")
        emisor("=" * 60)
        for idx, paq in enumerate(proyecto.paquetes, 1):
            totalActivas = len(obtenerTareasActivas(paq))
            emisor(
                f"  {idx}. [{paq.idPaquete}] {paq.nombre} ({totalActivas} tareas activas)"
            )
        emisor("  0. Volver al Menú del Proyecto")

        sel = lector("\nSeleccione el número del paquete a operar: ").strip()
        if sel == "0" or sel.lower() == "cancelar":
            break
        if sel.isdigit() and 1 <= int(sel) <= len(proyecto.paquetes):
            paqElegido = proyecto.paquetes[int(sel) - 1]
            operarTableroPaquete(
                conexion, idProyecto, paqElegido.idPaquete, lector, emisor
            )
        else:
            emisor("⚠️  Selección inválida. Ingrese un número de paquete válido.")
