"""Catálogos y enumeraciones inmutables de dominio para AgilBan.

Define los tipos de proyectos, cargos de integrantes, prioridades de tareas,
estados del tablero Kanban y estados derivados de paquetes de trabajo.
"""

from enum import Enum


class TipoProyecto(Enum):
    """Catálogo de tipos de proyecto admitidos en el sistema."""

    DESARROLLO_WEB = "Desarrollo Web"
    APLICACION_MOVIL = "Aplicación Móvil"
    CIENCIA_DATOS_IA = "Ciencia de Datos / IA"
    INFRAESTRUCTURA_REDES = "Infraestructura y Redes"
    MARKETING_DISENO = "Marketing y Diseño"
    INVESTIGACION_ACADEMICA = "Investigación Académica"


class CargoIntegrante(Enum):
    """Catálogo de cargos o roles disponibles para los integrantes."""

    LIDER_PROYECTO = "Líder de Proyecto"
    DESARROLLADOR_BACKEND = "Desarrollador Backend"
    DESARROLLADOR_FRONTEND = "Desarrollador Frontend"
    DESARROLLADOR_FULLSTACK = "Desarrollador Fullstack"
    INGENIERO_QA = "Ingeniero QA / Tester"
    DISENADOR_UI_UX = "Diseñador UI/UX"
    ANALISTA_DATOS = "Analista de Datos"


class PrioridadTarea(Enum):
    """Niveles de prioridad asignables a las tareas."""

    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"
    CRITICA = "Crítica"


class EstadoKanban(Enum):
    """Estados del ciclo de vida de una tarea en el tablero Kanban de 4 columnas."""

    PENDIENTE = "Pendiente"
    EN_PROGRESO = "En progreso"
    EN_REVISION = "En revisión"
    TERMINADA = "Terminada"


class EstadoPaquete(Enum):
    """Estados calculados de forma declarativa para un paquete de trabajo."""

    SIN_TAREAS = "Sin Tareas"
    PENDIENTE = "Pendiente"
    EN_PROGRESO = "En progreso"
    TERMINADO = "Terminado"
