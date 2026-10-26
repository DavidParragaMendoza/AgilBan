"""Modelos y entidades inmutables del dominio para AgilBan.

Implementa el pilar 6 de programación funcional:
Inmutabilidad estricta mediante @dataclass(frozen=True) y colecciones inmutables tuple[...].
Cualquier modificación genera una nueva versión mediante transformaciones puras (dataclasses.replace).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.catalogos import (
    CargoIntegrante,
    EstadoKanban,
    PrioridadTarea,
    TipoProyecto,
)
from app.domain.monadas import Ninguno, Opcion


@dataclass(frozen=True)
class TransicionHistorial:
    """Registro inmutable de una transición o devolución de estado en una tarea."""

    idTransicion: str
    idTarea: str
    estadoOrigen: EstadoKanban
    estadoDestino: EstadoKanban
    fechaHora: str
    comentario: Opcion[str] = field(default_factory=Ninguno)


@dataclass(frozen=True)
class EventoCreacionTarea:
    """Registro inmutable de la creación original de una tarea."""

    idTarea: str
    fechaHora: str


@dataclass(frozen=True)
class Tarea:
    """Entidad inmutable que representa una unidad de trabajo asignable."""

    idTarea: str
    idPaquete: str
    titulo: str
    descripcion: Opcion[str] = field(default_factory=Ninguno)
    prioridad: PrioridadTarea = PrioridadTarea.MEDIA
    cedulaResponsable: Opcion[str] = field(default_factory=Ninguno)
    fechaObjetivo: Opcion[str] = field(default_factory=Ninguno)
    estado: EstadoKanban = EstadoKanban.PENDIENTE
    contadorRegresos: int = 0
    activo: bool = True
    historial: tuple[TransicionHistorial, ...] = ()
    eventoCreacion: Opcion[EventoCreacionTarea] = field(default_factory=Ninguno)


@dataclass(frozen=True)
class PaqueteTrabajo:
    """Contenedor inmutable de la Estructura de Desglose del Trabajo (EDT)."""

    idPaquete: str
    idProyecto: str
    nombre: str
    tareas: tuple[Tarea, ...] = ()


@dataclass(frozen=True)
class Integrante:
    """Miembro de un equipo asignado a un proyecto específico."""

    cedula: str
    idProyecto: str
    nombre: str
    cargo: CargoIntegrante


@dataclass(frozen=True)
class Proyecto:
    """Entidad raíz agregada del sistema de gestión ágil."""

    idProyecto: str
    nombre: str
    tipo: TipoProyecto
    paquetes: tuple[PaqueteTrabajo, ...] = ()
    integrantes: tuple[Integrante, ...] = ()
