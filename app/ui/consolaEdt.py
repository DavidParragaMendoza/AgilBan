# ruff: noqa: N999
"""Módulo de gestión interactiva de la EDT, Integrantes y Descarte Lógico en consola.

Permite administrar la estructura jerárquica de paquetes de trabajo, la nómina
de integrantes del equipo y el descarte de tareas por borrado lógico asegurando
las validaciones puras del dominio y persistencia atómica en SQLite.
"""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Callable

from app.adapters.repositorioSqlite import (
    actualizarNombrePaquete,
    eliminarIntegrante,
    eliminarPaqueteVacio,
    guardarProyectoCompleto,
    guardarTareaConHistorial,
    recuperarProyectos,
)
from app.core.edt import (
    agregarPaqueteAProyecto,
    obtenerTareasActivas,
    renombrarPaquete,
)
from app.core.kanban import descartarTareaLogicamente
from app.core.validador import (
    validarCedula,
    validarEliminacionIntegrante,
    validarEliminacionPaquete,
    validarNombreIntegrante,
    validarNombrePaquete,
)
from app.domain.catalogos import CargoIntegrante
from app.domain.modelos import Integrante, PaqueteTrabajo, Proyecto
from app.domain.monadas import Exito, Fallo
from app.ui.formateadores import (
    formatearTablaEDT,
    formatearTablaIntegrantes,
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


def seleccionarCargo(
    lector: Callable[[str], str], emisor: Callable[[str], None]
) -> CargoIntegrante:
    """Solicita al usuario seleccionar un cargo válido del catálogo."""
    cargos = list(CargoIntegrante)
    while True:
        emisor("\nSeleccione el cargo del nuevo integrante:")
        for idx, cargo in enumerate(cargos, 1):
            emisor(f"  {idx}. {cargo.value}")
        entrada = lector(
            f"Seleccione una opción (1-{len(cargos)}) [por defecto 1]: "
        ).strip()
        if not entrada:
            return cargos[0]
        if entrada.isdigit() and 1 <= int(entrada) <= len(cargos):
            return cargos[int(entrada) - 1]
        emisor("⚠️  Opción no válida. Ingrese un número de la lista.")


def agregarNuevoPaquete(
    conexion: sqlite3.Connection,
    proyecto: Proyecto,
    lector: Callable[[str], str],
    emisor: Callable[[str], None],
) -> None:
    """Guía la incorporación de un nuevo paquete de trabajo a la EDT."""
    emisor("\n--- Agregar Nuevo Paquete de Trabajo ---")
    nombresExistentes = tuple(p.nombre for p in proyecto.paquetes)

    while True:
        nombre = lector("Nombre del paquete (o '0' para cancelar): ").strip()
        if nombre == "0" or nombre.lower() == "cancelar":
            emisor("Operación cancelada.")
            return

        resVal = validarNombrePaquete(nombre, nombresExistentes)
        match resVal:
            case Fallo(err):
                emisor(f"⚠️  {err.mensaje}")
            case Exito(nombreValido):
                idPaquete = f"PAQ-{len(proyecto.paquetes) + 1:03d}-{uuid.uuid4().hex[:3].upper()}"
                nuevoPaquete = PaqueteTrabajo(
                    idPaquete=idPaquete,
                    idProyecto=proyecto.idProyecto,
                    nombre=nombreValido,
                    tareas=(),
                )
                proyectoActualizado = agregarPaqueteAProyecto(proyecto, nuevoPaquete)
                resGuardar = guardarProyectoCompleto(conexion, proyectoActualizado)
                match resGuardar:
                    case Exito(_):
                        emisor(
                            f"\n🎉 ¡Paquete de trabajo '{nombreValido}' [{idPaquete}] agregado exitosamente a la EDT!"
                        )
                    case Fallo(err):
                        emisor(f"❌ Error al guardar en base de datos: {err}")
                return


def renombrarPaqueteExistente(
    conexion: sqlite3.Connection,
    proyecto: Proyecto,
    lector: Callable[[str], str],
    emisor: Callable[[str], None],
) -> None:
    """Permite renombrar un paquete existente respetando reglas de unicidad."""
    if not proyecto.paquetes:
        emisor("\n⚠️  No hay paquetes de trabajo en este proyecto.")
        return

    emisor("\n--- Renombrar Paquete de Trabajo ---")
    for idx, p in enumerate(proyecto.paquetes, 1):
        emisor(f"  {idx}. [{p.idPaquete}] {p.nombre}")

    sel = lector("\nSeleccione el número del paquete (o '0' para cancelar): ").strip()
    if sel == "0" or not sel.isdigit() or not (1 <= int(sel) <= len(proyecto.paquetes)):
        emisor("Operación cancelada.")
        return

    paquete = proyecto.paquetes[int(sel) - 1]
    nuevoNombre = lector(
        f"Nuevo nombre para '{paquete.nombre}' (o '0' para cancelar): "
    ).strip()
    if nuevoNombre == "0" or not nuevoNombre:
        emisor("Operación cancelada.")
        return

    resRenombrar = renombrarPaquete(proyecto, paquete.idPaquete, nuevoNombre)
    match resRenombrar:
        case Fallo(err):
            emisor(f"⚠️  {err.mensaje}")
        case Exito(_):
            resSql = actualizarNombrePaquete(conexion, paquete.idPaquete, nuevoNombre)
            match resSql:
                case Exito(_):
                    emisor(
                        f"\n✅ Paquete [{paquete.idPaquete}] renombrado exitosamente a '{nuevoNombre.strip()}'."
                    )
                case Fallo(err):
                    emisor(f"❌ Error en base de datos: {err}")


def eliminarPaqueteTrabajo(
    conexion: sqlite3.Connection,
    proyecto: Proyecto,
    lector: Callable[[str], str],
    emisor: Callable[[str], None],
) -> None:
    """Elimina un paquete vacío, bloqueando si contiene tareas asociadas."""
    if not proyecto.paquetes:
        emisor("\n⚠️  No hay paquetes de trabajo registrados.")
        return

    emisor("\n--- Eliminar Paquete de Trabajo ---")
    for idx, p in enumerate(proyecto.paquetes, 1):
        totalTareas = len(p.tareas)
        emisor(f"  {idx}. [{p.idPaquete}] {p.nombre} ({totalTareas} tareas asociadas)")

    sel = lector(
        "\nSeleccione el número del paquete a eliminar (o '0' para cancelar): "
    ).strip()
    if sel == "0" or not sel.isdigit() or not (1 <= int(sel) <= len(proyecto.paquetes)):
        emisor("Operación cancelada.")
        return

    paquete = proyecto.paquetes[int(sel) - 1]
    resValidar = validarEliminacionPaquete(paquete)

    match resValidar:
        case Fallo(err):
            emisor(f"\n❌ Operación bloqueada: {err.mensaje}")
        case Exito(_):
            confirmacion = (
                lector(
                    f"¿Está seguro de eliminar el paquete '{paquete.nombre}'? (S/N): "
                )
                .strip()
                .upper()
            )
            if confirmacion != "S":
                emisor("Operación cancelada por el usuario.")
                return

            resEliminar = eliminarPaqueteVacio(conexion, paquete.idPaquete)
            match resEliminar:
                case Exito(_):
                    emisor(
                        f"\n🗑️ Paquete '{paquete.nombre}' eliminado exitosamente de la EDT."
                    )
                case Fallo(err):
                    emisor(f"❌ Error al eliminar en base de datos: {err}")


def agregarNuevoIntegrante(
    conexion: sqlite3.Connection,
    proyecto: Proyecto,
    lector: Callable[[str], str],
    emisor: Callable[[str], None],
) -> None:
    """Registra y valida un nuevo integrante para el equipo del proyecto."""
    emisor("\n--- Agregar Nuevo Integrante al Equipo ---")
    cedulasExistentes = tuple(i.cedula for i in proyecto.integrantes)

    # 1. Cédula
    cedula = ""
    while True:
        cedula = lector("Cédula (10 dígitos numéricos) o '0' para cancelar: ").strip()
        if cedula == "0" or cedula.lower() == "cancelar":
            emisor("Operación cancelada.")
            return

        resCedula = validarCedula(cedula, cedulasExistentes)
        match resCedula:
            case Fallo(err):
                emisor(f"⚠️  {err.mensaje}")
            case Exito(cedulaValida):
                cedula = cedulaValida
                break

    # 2. Nombre
    nombre = ""
    while True:
        nombre = lector("Nombre y Apellido del integrante: ").strip()
        resNombre = validarNombreIntegrante(nombre)
        match resNombre:
            case Fallo(err):
                emisor(f"⚠️  {err.mensaje}")
            case Exito(nombreValido):
                nombre = nombreValido
                break

    # 3. Cargo
    cargo = seleccionarCargo(lector, emisor)

    nuevoIntegrante = Integrante(
        cedula=cedula,
        idProyecto=proyecto.idProyecto,
        nombre=nombre,
        cargo=cargo,
    )
    nuevoProyecto = Proyecto(
        idProyecto=proyecto.idProyecto,
        nombre=proyecto.nombre,
        tipo=proyecto.tipo,
        paquetes=proyecto.paquetes,
        integrantes=proyecto.integrantes + (nuevoIntegrante,),
    )
    resGuardar = guardarProyectoCompleto(conexion, nuevoProyecto)
    match resGuardar:
        case Exito(_):
            emisor(
                f"\n🎉 ¡Integrante '{nombre}' ({cargo.value}) incorporado exitosamente al equipo!"
            )
        case Fallo(err):
            emisor(f"❌ Error al guardar integrante: {err}")


def eliminarIntegranteEquipo(
    conexion: sqlite3.Connection,
    proyecto: Proyecto,
    lector: Callable[[str], str],
    emisor: Callable[[str], None],
) -> None:
    """Elimina a un integrante validando reglas de último miembro y tareas activas."""
    emisor("\n--- Eliminar Integrante del Equipo ---")
    for idx, i in enumerate(proyecto.integrantes, 1):
        emisor(f"  {idx}. [{i.cedula}] {i.nombre} ({i.cargo.value})")

    sel = lector(
        "\nSeleccione el integrante a eliminar (o '0' para cancelar): "
    ).strip()
    if (
        sel == "0"
        or not sel.isdigit()
        or not (1 <= int(sel) <= len(proyecto.integrantes))
    ):
        emisor("Operación cancelada.")
        return

    integrante = proyecto.integrantes[int(sel) - 1]
    todasTareas = tuple(t for paq in proyecto.paquetes for t in paq.tareas)

    resValidar = validarEliminacionIntegrante(
        integrante.cedula, proyecto.integrantes, todasTareas
    )
    match resValidar:
        case Fallo(err):
            emisor(f"\n❌ Operación bloqueada: {err.mensaje}")
        case Exito(_):
            confirmacion = (
                lector(f"¿Confirmar la eliminación de '{integrante.nombre}'? (S/N): ")
                .strip()
                .upper()
            )
            if confirmacion != "S":
                emisor("Operación cancelada por el usuario.")
                return

            resSql = eliminarIntegrante(
                conexion, integrante.cedula, proyecto.idProyecto
            )
            match resSql:
                case Exito(_):
                    emisor(
                        f"\n🗑️ Integrante '{integrante.nombre}' desvinculado exitosamente del proyecto."
                    )
                case Fallo(err):
                    emisor(f"❌ Error al eliminar integrante: {err}")


def descartarTareaEnEdt(
    conexion: sqlite3.Connection,
    proyecto: Proyecto,
    lector: Callable[[str], str],
    emisor: Callable[[str], None],
) -> None:
    """Ejecuta el borrado lógico de una tarea activa (activo = False)."""
    emisor("\n--- Descarte Lógico de Tarea (Borrado Lógico) ---")

    # Obtener todas las tareas activas agrupadas por paquete
    paquetesConActivas = [
        (paq, obtenerTareasActivas(paq))
        for paq in proyecto.paquetes
        if len(obtenerTareasActivas(paq)) > 0
    ]

    if not paquetesConActivas:
        emisor(
            "\n⚠️  No hay tareas activas disponibles para descartar en este proyecto."
        )
        return

    emisor("\nSeleccione el paquete de trabajo de la tarea:")
    for idx, (paq, tareasActivas) in enumerate(paquetesConActivas, 1):
        emisor(
            f"  {idx}. [{paq.idPaquete}] {paq.nombre} ({len(tareasActivas)} tareas activas)"
        )

    selPaq = lector("\nNúmero de paquete (o '0' para cancelar): ").strip()
    if (
        selPaq == "0"
        or not selPaq.isdigit()
        or not (1 <= int(selPaq) <= len(paquetesConActivas))
    ):
        emisor("Operación cancelada.")
        return

    paqElegido, tareasActivas = paquetesConActivas[int(selPaq) - 1]

    emisor(f"\nTareas activas en [{paqElegido.nombre}]:")
    for idx, t in enumerate(tareasActivas, 1):
        emisor(f"  {idx}. [{t.idTarea}] {t.titulo} ({t.estado.value})")

    selTarea = lector("\nNúmero de tarea a descartar (o '0' para cancelar): ").strip()
    if (
        selTarea == "0"
        or not selTarea.isdigit()
        or not (1 <= int(selTarea) <= len(tareasActivas))
    ):
        emisor("Operación cancelada.")
        return

    tareaElegida = tareasActivas[int(selTarea) - 1]
    confirmacion = (
        lector(
            f"¿Está seguro de descartar lógicamente la tarea '{tareaElegida.titulo}'? (S/N): "
        )
        .strip()
        .upper()
    )
    if confirmacion != "S":
        emisor("Operación cancelada por el usuario.")
        return

    tareaDescartada = descartarTareaLogicamente(tareaElegida)
    resGuardar = guardarTareaConHistorial(conexion, tareaDescartada)

    match resGuardar:
        case Exito(_):
            emisor(
                f"\n🗑️ Tarea [{tareaDescartada.idTarea}] '{tareaDescartada.titulo}' descartada lógicamente."
            )
            emisor(
                "   (Ha sido retirada del tablero Kanban, preservándose íntegra para auditoría y métricas)."
            )
        case Fallo(err):
            emisor(f"❌ Error al guardar borrado lógico: {err}")


def ejecutarMenuEdt(
    conexion: sqlite3.Connection,
    idProyecto: str,
    lector: Callable[[str], str] = input,
    emisor: Callable[[str], None] = print,
) -> None:
    """Controla el menú operativo para gestionar la EDT, equipo y descarte de tareas."""
    while True:
        proyecto = buscarProyectoPorId(conexion, idProyecto)
        if not proyecto:
            emisor("❌ Error: Proyecto no encontrado en base de datos.")
            break

        emisor("\n" + "=" * 65)
        emisor(f"     GESTIÓN DE EDT Y EQUIPO — {proyecto.nombre.upper()}")
        emisor("=" * 65)
        emisor("1. Ver estructura jerárquica de la EDT")
        emisor("2. Ver equipo de integrantes")
        emisor("3. Agregar nuevo paquete de trabajo")
        emisor("4. Renombrar paquete de trabajo")
        emisor("5. Eliminar paquete de trabajo vacío")
        emisor("6. Agregar integrante al equipo")
        emisor("7. Eliminar integrante del equipo")
        emisor("8. Descartar tarea lógicamente (Borrado lógico)")
        emisor("0. Volver al Menú del Proyecto")

        opcion = lector("\nSeleccione una opción: ").strip()

        match opcion:
            case "1":
                emisor("\n" + formatearTablaEDT(proyecto))
            case "2":
                emisor("\n" + formatearTablaIntegrantes(proyecto.integrantes))
            case "3":
                agregarNuevoPaquete(conexion, proyecto, lector, emisor)
            case "4":
                renombrarPaqueteExistente(conexion, proyecto, lector, emisor)
            case "5":
                eliminarPaqueteTrabajo(conexion, proyecto, lector, emisor)
            case "6":
                agregarNuevoIntegrante(conexion, proyecto, lector, emisor)
            case "7":
                eliminarIntegranteEquipo(conexion, proyecto, lector, emisor)
            case "8":
                descartarTareaEnEdt(conexion, proyecto, lector, emisor)
            case "0":
                break
            case _:
                emisor("⚠️  Opción no válida. Ingrese un número del 0 al 8.")
