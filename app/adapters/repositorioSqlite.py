# ruff: noqa: N999
"""Módulo de repositorio y persistencia relacional transaccional en SQLite3.

Garantiza atomicidad, integridad referencial y reconstrucción inmutable
para proyectos, integrantes, paquetes de trabajo, tareas e historial.
"""

from __future__ import annotations

import sqlite3

from app.adapters.telemetria import cronometrarOperacion
from app.domain.catalogos import (
    CargoIntegrante,
    EstadoKanban,
    PrioridadTarea,
    TipoProyecto,
)
from app.domain.modelos import (
    Integrante,
    PaqueteTrabajo,
    Proyecto,
    Tarea,
    TransicionHistorial,
)
from app.domain.monadas import Alguno, Exito, Fallo, Ninguno, Resultado


@cronometrarOperacion(nombrePersonalizado="guardarProyectoCompleto")
def guardarProyectoCompleto(
    conexion: sqlite3.Connection,
    proyecto: Proyecto,
) -> Resultado[None, str]:
    """Guarda o actualiza atómicamente un proyecto con sus integrantes, paquetes y tareas asociadas."""
    try:
        with conexion:
            cursor = conexion.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO proyectos (id_proyecto, nombre, tipo)
                   VALUES (?, ?, ?)""",
                (proyecto.idProyecto, proyecto.nombre, proyecto.tipo.value),
            )

            for integrante in proyecto.integrantes:
                cursor.execute(
                    """INSERT OR REPLACE INTO integrantes (cedula, id_proyecto, nombre, cargo)
                       VALUES (?, ?, ?, ?)""",
                    (
                        integrante.cedula,
                        integrante.idProyecto,
                        integrante.nombre,
                        integrante.cargo.value,
                    ),
                )

            for paquete in proyecto.paquetes:
                cursor.execute(
                    """INSERT OR REPLACE INTO paquetes_trabajo (id_paquete, id_proyecto, nombre)
                       VALUES (?, ?, ?)""",
                    (paquete.idPaquete, paquete.idProyecto, paquete.nombre),
                )

                for tarea in paquete.tareas:
                    descValor = (
                        tarea.descripcion.obtenerValor()
                        if tarea.descripcion.esAlguno()
                        else None
                    )
                    respValor = (
                        tarea.cedulaResponsable.obtenerValor()
                        if tarea.cedulaResponsable.esAlguno()
                        else None
                    )
                    fechaValor = (
                        tarea.fechaObjetivo.obtenerValor()
                        if tarea.fechaObjetivo.esAlguno()
                        else None
                    )

                    cursor.execute(
                        """INSERT OR REPLACE INTO tareas
                           (id_tarea, id_paquete, titulo, descripcion, prioridad,
                            cedula_responsable, fecha_objetivo, estado, contador_regresos, activo)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            tarea.idTarea,
                            tarea.idPaquete,
                            tarea.titulo,
                            descValor,
                            tarea.prioridad.value,
                            respValor,
                            fechaValor,
                            tarea.estado.value,
                            tarea.contadorRegresos,
                            1 if tarea.activo else 0,
                        ),
                    )

                    for trans in tarea.historial:
                        comentValor = (
                            trans.comentario.obtenerValor()
                            if trans.comentario.esAlguno()
                            else None
                        )
                        cursor.execute(
                            """INSERT OR REPLACE INTO historial_transiciones
                               (id_transicion, id_tarea, estado_origen, estado_destino, fecha_hora, comentario)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (
                                trans.idTransicion,
                                trans.idTarea,
                                trans.estadoOrigen.value,
                                trans.estadoDestino.value,
                                trans.fechaHora,
                                comentValor,
                            ),
                        )

        return Exito(None)
    except sqlite3.Error as error:
        return Fallo(f"Error al guardar el proyecto completo: {error}")


@cronometrarOperacion(nombrePersonalizado="recuperarProyectos")
def recuperarProyectos(
    conexion: sqlite3.Connection,
) -> Resultado[tuple[Proyecto, ...], str]:
    """Reconstruye la jerarquía inmutable completa de proyectos, integrantes, paquetes y tareas."""
    try:
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT id_proyecto, nombre, tipo FROM proyectos ORDER BY nombre ASC"
        )
        filasProyectos = cursor.fetchall()

        listaProyectos: list[Proyecto] = []

        for idProyecto, nombreProy, tipoProy in filasProyectos:
            cursor.execute(
                """SELECT cedula, id_proyecto, nombre, cargo
                   FROM integrantes
                   WHERE id_proyecto = ?
                   ORDER BY nombre ASC""",
                (idProyecto,),
            )
            filasIntegrantes = cursor.fetchall()
            integrantes = tuple(
                Integrante(
                    cedula=ced,
                    idProyecto=idProy,
                    nombre=nom,
                    cargo=CargoIntegrante(cargoStr),
                )
                for ced, idProy, nom, cargoStr in filasIntegrantes
            )

            cursor.execute(
                """SELECT id_paquete, id_proyecto, nombre
                   FROM paquetes_trabajo
                   WHERE id_proyecto = ?
                   ORDER BY id_paquete ASC""",
                (idProyecto,),
            )
            filasPaquetes = cursor.fetchall()
            listaPaquetes: list[PaqueteTrabajo] = []

            for idPaq, idProyPaq, nomPaq in filasPaquetes:
                cursor.execute(
                    """SELECT id_tarea, id_paquete, titulo, descripcion, prioridad,
                              cedula_responsable, fecha_objetivo, estado, contador_regresos, activo
                       FROM tareas
                       WHERE id_paquete = ?
                       ORDER BY id_tarea ASC""",
                    (idPaq,),
                )
                filasTareas = cursor.fetchall()
                listaTareas: list[Tarea] = []

                for (
                    idTar,
                    idPaqTar,
                    titTar,
                    descTar,
                    prioTar,
                    respTar,
                    fechaTar,
                    estTar,
                    regTar,
                    actTar,
                ) in filasTareas:
                    cursor.execute(
                        """SELECT id_transicion, id_tarea, estado_origen, estado_destino, fecha_hora, comentario
                           FROM historial_transiciones
                           WHERE id_tarea = ?
                           ORDER BY fecha_hora ASC""",
                        (idTar,),
                    )
                    filasHistorial = cursor.fetchall()
                    historial = tuple(
                        TransicionHistorial(
                            idTransicion=idTr,
                            idTarea=idTarTr,
                            estadoOrigen=EstadoKanban(estOrig),
                            estadoDestino=EstadoKanban(estDest),
                            fechaHora=fHora,
                            comentario=Alguno(coment)
                            if coment is not None
                            else Ninguno(),
                        )
                        for idTr, idTarTr, estOrig, estDest, fHora, coment in filasHistorial
                    )

                    tarea = Tarea(
                        idTarea=idTar,
                        idPaquete=idPaqTar,
                        titulo=titTar,
                        descripcion=Alguno(descTar)
                        if descTar is not None
                        else Ninguno(),
                        prioridad=PrioridadTarea(prioTar),
                        cedulaResponsable=Alguno(respTar)
                        if respTar is not None
                        else Ninguno(),
                        fechaObjetivo=Alguno(fechaTar)
                        if fechaTar is not None
                        else Ninguno(),
                        estado=EstadoKanban(estTar),
                        contadorRegresos=regTar,
                        activo=bool(actTar),
                        historial=historial,
                    )
                    listaTareas.append(tarea)

                paquete = PaqueteTrabajo(
                    idPaquete=idPaq,
                    idProyecto=idProyPaq,
                    nombre=nomPaq,
                    tareas=tuple(listaTareas),
                )
                listaPaquetes.append(paquete)

            proyecto = Proyecto(
                idProyecto=idProyecto,
                nombre=nombreProy,
                tipo=TipoProyecto(tipoProy),
                paquetes=tuple(listaPaquetes),
                integrantes=integrantes,
            )
            listaProyectos.append(proyecto)

        return Exito(tuple(listaProyectos))
    except (sqlite3.Error, ValueError) as error:
        return Fallo(f"Error al recuperar los proyectos: {error}")


@cronometrarOperacion(nombrePersonalizado="actualizarNombrePaquete")
def actualizarNombrePaquete(
    conexion: sqlite3.Connection,
    idPaquete: str,
    nuevoNombre: str,
) -> Resultado[None, str]:
    """Actualiza el nombre de un paquete de trabajo verificando restricciones de unicidad."""
    try:
        with conexion:
            cursor = conexion.cursor()
            cursor.execute(
                """UPDATE paquetes_trabajo
                   SET nombre = ?
                   WHERE id_paquete = ?""",
                (nuevoNombre.strip(), idPaquete),
            )
            if cursor.rowcount == 0:
                return Fallo(
                    f"No se encontró el paquete con identificador '{idPaquete}'."
                )
        return Exito(None)
    except sqlite3.IntegrityError as error:
        return Fallo(
            f"Ya existe un paquete con el nombre '{nuevoNombre}' en este proyecto: {error}"
        )
    except sqlite3.Error as error:
        return Fallo(f"Error al actualizar el nombre del paquete: {error}")


@cronometrarOperacion(nombrePersonalizado="eliminarPaqueteVacio")
def eliminarPaqueteVacio(
    conexion: sqlite3.Connection,
    idPaquete: str,
) -> Resultado[None, str]:
    """Elimina un paquete de trabajo verificando previamente que no tenga tareas asociadas."""
    try:
        with conexion:
            cursor = conexion.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM tareas WHERE id_paquete = ?", (idPaquete,)
            )
            totalTareas = cursor.fetchone()[0]
            if totalTareas > 0:
                return Fallo(
                    f"No es posible eliminar el paquete '{idPaquete}' porque contiene {totalTareas} tarea(s) asociada(s)."
                )

            cursor.execute(
                "DELETE FROM paquetes_trabajo WHERE id_paquete = ?",
                (idPaquete,),
            )
            if cursor.rowcount == 0:
                return Fallo(
                    f"No se encontró el paquete con identificador '{idPaquete}'."
                )

        return Exito(None)
    except sqlite3.Error as error:
        return Fallo(f"Error al eliminar el paquete de trabajo: {error}")


@cronometrarOperacion(nombrePersonalizado="eliminarIntegrante")
def eliminarIntegrante(
    conexion: sqlite3.Connection,
    cedula: str,
    idProyecto: str,
) -> Resultado[None, str]:
    """Elimina un integrante del proyecto validando que no sea el único ni tenga tareas activas asignadas."""
    try:
        with conexion:
            cursor = conexion.cursor()

            # Verificar si es el único integrante del proyecto
            cursor.execute(
                "SELECT COUNT(*) FROM integrantes WHERE id_proyecto = ?",
                (idProyecto,),
            )
            totalIntegrantes = cursor.fetchone()[0]
            if totalIntegrantes <= 1:
                return Fallo("No es posible eliminar al único integrante del proyecto.")

            # Verificar si tiene tareas activas asignadas en el proyecto
            cursor.execute(
                """SELECT COUNT(*)
                   FROM tareas t
                   JOIN paquetes_trabajo p ON t.id_paquete = p.id_paquete
                   WHERE p.id_proyecto = ?
                     AND t.cedula_responsable = ?
                     AND t.activo = 1""",
                (idProyecto, cedula),
            )
            tareasActivasAsignadas = cursor.fetchone()[0]
            if tareasActivasAsignadas > 0:
                return Fallo(
                    f"No es posible eliminar al integrante '{cedula}' porque tiene {tareasActivasAsignadas} tarea(s) activa(s) asignada(s)."
                )

            cursor.execute(
                "DELETE FROM integrantes WHERE cedula = ? AND id_proyecto = ?",
                (cedula, idProyecto),
            )
            if cursor.rowcount == 0:
                return Fallo(
                    f"No se encontró al integrante con cédula '{cedula}' en el proyecto '{idProyecto}'."
                )

        return Exito(None)
    except sqlite3.Error as error:
        return Fallo(f"Error al eliminar al integrante: {error}")
