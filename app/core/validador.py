"""Módulo de validaciones funcionales puras para el núcleo de AgilBan.

Implementa funciones deterministas y puras para validar reglas de negocio,
formatos e invariantes de proyectos, integrantes, paquetes y tareas,
retornando contenedores mónadas Resultado[T, E].
"""

from __future__ import annotations

import re

from app.domain.errores import (
    ErrorDuplicado,
    ErrorReglaNegocio,
    ErrorValidacion,
)
from app.domain.modelos import Integrante, Tarea
from app.domain.monadas import Alguno, Exito, Fallo, Resultado

_PATRON_CEDULA = re.compile(r"^\d{10}$")
_PATRON_NOMBRE_PERSONA = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$")


def validarNombreProyecto(
    nombre: str, nombresExistentes: tuple[str, ...]
) -> Resultado[str, ErrorValidacion | ErrorDuplicado]:
    """Valida formato, longitud y unicidad (case-insensitive) del nombre de un proyecto."""
    nombreLimpio = nombre.strip()
    if not nombreLimpio:
        return Fallo(
            ErrorValidacion(
                mensaje="El nombre del proyecto no puede estar vacío.",
                campo="nombre",
            )
        )
    if len(nombreLimpio) > 100:
        return Fallo(
            ErrorValidacion(
                mensaje="El nombre del proyecto no puede superar los 100 caracteres.",
                campo="nombre",
            )
        )

    nombreMinusculas = nombreLimpio.lower()
    if any(
        existente.strip().lower() == nombreMinusculas for existente in nombresExistentes
    ):
        return Fallo(
            ErrorDuplicado(
                mensaje=f"Ya existe un proyecto con el nombre '{nombreLimpio}'.",
                entidad="Proyecto",
                identificador=nombreLimpio,
            )
        )

    return Exito(nombreLimpio)


def validarCedula(
    cedula: str, cedulasProyecto: tuple[str, ...]
) -> Resultado[str, ErrorValidacion | ErrorDuplicado]:
    """Valida formato de 10 dígitos numéricos y unicidad de cédula dentro del proyecto."""
    cedulaLimpia = cedula.strip()
    if not _PATRON_CEDULA.fullmatch(cedulaLimpia):
        return Fallo(
            ErrorValidacion(
                mensaje="La cédula debe contener exactamente 10 dígitos numéricos.",
                campo="cedula",
            )
        )

    if cedulaLimpia in cedulasProyecto:
        return Fallo(
            ErrorDuplicado(
                mensaje=f"La cédula '{cedulaLimpia}' ya está registrada en este proyecto.",
                entidad="Integrante",
                identificador=cedulaLimpia,
            )
        )

    return Exito(cedulaLimpia)


def validarNombreIntegrante(nombre: str) -> Resultado[str, ErrorValidacion]:
    """Valida longitud y caracteres alfabéticos para el nombre de un integrante."""
    nombreLimpio = nombre.strip()
    if not nombreLimpio:
        return Fallo(
            ErrorValidacion(
                mensaje="El nombre del integrante no puede estar vacío.",
                campo="nombre",
            )
        )
    if len(nombreLimpio) > 80:
        return Fallo(
            ErrorValidacion(
                mensaje="El nombre del integrante no puede superar los 80 caracteres.",
                campo="nombre",
            )
        )
    if not _PATRON_NOMBRE_PERSONA.fullmatch(nombreLimpio):
        return Fallo(
            ErrorValidacion(
                mensaje="El nombre del integrante solo puede contener letras y espacios.",
                campo="nombre",
            )
        )

    return Exito(nombreLimpio)


def validarEliminacionIntegrante(
    cedula: str, integrantes: tuple[Integrante, ...], tareas: tuple[Tarea, ...]
) -> Resultado[str, ErrorReglaNegocio]:
    """Valida que el integrante no sea el último del proyecto ni tenga tareas activas asignadas."""
    if len(integrantes) <= 1:
        return Fallo(
            ErrorReglaNegocio(
                mensaje="No es posible eliminar al único integrante del proyecto.",
                codigo="ULTIMO_INTEGRANTE",
            )
        )

    tieneTareasActivas = any(
        t.activo and t.cedulaResponsable == Alguno(cedula) for t in tareas
    )
    if tieneTareasActivas:
        return Fallo(
            ErrorReglaNegocio(
                mensaje="No es posible eliminar al integrante porque posee tareas activas asignadas.",
                codigo="INTEGRANTE_CON_TAREAS_ACTIVAS",
            )
        )

    return Exito(cedula)
