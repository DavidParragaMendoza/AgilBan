"""Diccionario central y tokens de diseno Tailwind CSS para la interfaz web de AgilBan.

Define constantes inmutables para paletas de color, tipografias, sombras de tarjetas,
modales, insignias de prioridad y estados de Kanban/EDT, conforme a RNF-01 (Fidelidad visual
con Google Stitch, NotebookLM y Notion) y RNF-05 (Nomenclatura 100% en espanol).
"""

from __future__ import annotations

from app.domain.catalogos import (
    EstadoKanban,
    EstadoPaquete,
    PrioridadTarea,
)

# ==============================================================================
# 1. LIENZOS, CONTENEDORES Y FONDOS (ESTILO NOTEBOOKLM / NOTION)
# ==============================================================================

FONDO_LIENZO: str = "min-h-screen bg-slate-50 text-slate-900 font-sans antialiased"
FONDO_SUPERFICIE: str = "bg-white"
FONDO_CONTENEDOR_SUAVE: str = "bg-slate-100"
FONDO_COLUMNA_KANBAN: str = "bg-slate-100/70 border border-slate-200/80 rounded-xl p-4 flex flex-col min-w-[280px] max-w-[340px] flex-1"

BORDE_SUAVE: str = "border border-slate-200"
BORDE_SUTIL: str = "border border-slate-100"
BORDE_DIVISOR: str = "divide-y divide-slate-100"

# ==============================================================================
# 2. TIPOGRAFIA Y JERARQUIA VISUAL
# ==============================================================================

TITULO_PANTALLA: str = "text-2xl font-bold text-slate-900 tracking-tight"
SUBTITULO_PANTALLA: str = "text-sm text-slate-500 mt-1"
TITULO_SECCION: str = "text-lg font-semibold text-slate-800 tracking-tight"
TITULO_TARJETA: str = "text-sm font-semibold text-slate-800 leading-snug"
TEXTO_MUTED: str = "text-xs text-slate-500"
TEXTO_CORPOREO: str = "text-sm text-slate-600 leading-relaxed"

# ==============================================================================
# 3. ELEVACION, SOMBRAS Y TARJETAS
# ==============================================================================

SOMBRA_NIVEL_0: str = "shadow-none"
SOMBRA_NIVEL_1: str = "shadow-sm"
SOMBRA_NIVEL_2: str = "shadow hover:shadow-md transition-shadow duration-200"
SOMBRA_NIVEL_3: str = "shadow-lg hover:shadow-xl transition-all duration-200"
SOMBRA_NIVEL_4: str = "shadow-2xl"

TARJETA_PROYECTO: str = (
    "bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md "
    "hover:border-indigo-300 transition-all duration-200 cursor-pointer flex flex-col justify-between"
)

TARJETA_KANBAN: str = (
    "bg-white border border-slate-200/80 rounded-lg p-3.5 shadow-sm hover:shadow "
    "transition-all duration-150 cursor-pointer space-y-2.5 group"
)

# ==============================================================================
# 4. BOTONES Y ACCIONES INTERACTIVAS
# ==============================================================================

BOTON_PRIMARIO: str = (
    "inline-flex items-center justify-center px-4 py-2 rounded-lg bg-indigo-600 "
    "text-white font-medium text-sm hover:bg-indigo-700 active:bg-indigo-800 "
    "transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 "
    "focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed"
)

BOTON_SECUNDARIO: str = (
    "inline-flex items-center justify-center px-4 py-2 rounded-lg bg-white "
    "border border-slate-200 text-slate-700 font-medium text-sm hover:bg-slate-50 "
    "hover:border-slate-300 active:bg-slate-100 transition-colors shadow-sm "
    "focus:outline-none focus:ring-2 focus:ring-slate-300 disabled:opacity-50 disabled:cursor-not-allowed"
)

BOTON_PELIGRO: str = (
    "inline-flex items-center justify-center px-4 py-2 rounded-lg bg-rose-600 "
    "text-white font-medium text-sm hover:bg-rose-700 active:bg-rose-800 "
    "transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-rose-500 "
    "disabled:opacity-50 disabled:cursor-not-allowed"
)

BOTON_FANTASMA: str = (
    "inline-flex items-center justify-center px-3 py-1.5 rounded-lg text-slate-600 "
    "hover:text-indigo-600 hover:bg-indigo-50 transition-colors text-sm font-medium "
    "focus:outline-none"
)

BOTON_ACCION_RAPIDA: str = (
    "inline-flex items-center justify-center px-2.5 py-1 rounded text-xs font-medium "
    "bg-slate-100 text-slate-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
)

# ==============================================================================
# 5. CAMPOS DE FORMULARIO, ENTRADAS Y ERRORES
# ==============================================================================

INPUT_TEXTO: str = (
    "w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-800 "
    "placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 "
    "focus:ring-indigo-100 transition-all"
)

INPUT_ERROR: str = (
    "w-full px-3 py-2 bg-white border border-rose-300 rounded-lg text-sm text-slate-800 "
    "placeholder-slate-400 focus:outline-none focus:border-rose-500 focus:ring-2 "
    "focus:ring-rose-100 transition-all"
)

TEXTO_ERROR_FORMULARIO: str = "text-xs text-rose-600 mt-1 font-medium block"

LABEL_FORMULARIO: str = (
    "block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1"
)

# ==============================================================================
# 6. MODALES Y SUPERPOSICIONES
# ==============================================================================

FONDO_MODAL_OVERLAY: str = "fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"

CONTENEDOR_MODAL: str = (
    "bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-lg w-full "
    "overflow-hidden flex flex-col max-h-[90vh] animate-in fade-in duration-150"
)

ENCABEZADO_MODAL: str = (
    "px-6 py-4 border-b border-slate-100 flex items-center justify-between"
)
CUERPO_MODAL: str = "p-6 overflow-y-auto space-y-4 flex-1"
PIE_MODAL: str = "px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end space-x-3"

# ==============================================================================
# 7. SIDE DRAWER Y AUTOGUARDADO (ESTILO NOTION)
# ==============================================================================

PANEL_LATERAL_DRAWER: str = (
    "fixed inset-y-0 right-0 w-full max-w-md bg-white shadow-2xl border-l border-slate-200 "
    "z-50 flex flex-col transform transition-transform duration-300 ease-in-out"
)

FONDO_DRAWER_OVERLAY: str = "fixed inset-0 bg-slate-900/20 backdrop-blur-[2px] z-40"

INDICADOR_GUARDANDO: str = (
    "text-xs text-amber-600 font-medium flex items-center space-x-1"
)
INDICADOR_GUARDADO: str = (
    "text-xs text-emerald-600 font-medium flex items-center space-x-1"
)
INDICADOR_ERROR_PERSISTENCIA: str = (
    "text-xs text-rose-600 font-medium flex items-center space-x-1"
)

# ==============================================================================
# 8. BADGES CROMATICOS DE PRIORIDAD DE TAREAS
# ==============================================================================

BADGE_PRIORIDAD_BAJA: str = (
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium "
    "bg-slate-100 text-slate-700 border border-slate-200"
)

BADGE_PRIORIDAD_MEDIA: str = (
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium "
    "bg-blue-50 text-blue-700 border border-blue-200"
)

BADGE_PRIORIDAD_ALTA: str = (
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium "
    "bg-amber-50 text-amber-800 border border-amber-200"
)

BADGE_PRIORIDAD_CRITICA: str = (
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold "
    "bg-rose-50 text-rose-700 border border-rose-200"
)

MAPA_CLASES_PRIORIDAD: dict[PrioridadTarea, str] = {
    PrioridadTarea.BAJA: BADGE_PRIORIDAD_BAJA,
    PrioridadTarea.MEDIA: BADGE_PRIORIDAD_MEDIA,
    PrioridadTarea.ALTA: BADGE_PRIORIDAD_ALTA,
    PrioridadTarea.CRITICA: BADGE_PRIORIDAD_CRITICA,
}


def obtenerClasePrioridad(prioridad: PrioridadTarea) -> str:
    """Retorna la clase Tailwind correspondiente a la prioridad de la tarea."""
    return MAPA_CLASES_PRIORIDAD.get(prioridad, BADGE_PRIORIDAD_MEDIA)


# ==============================================================================
# 9. BADGES CROMATICOS DE ESTADOS KANBAN
# ==============================================================================

BADGE_ESTADO_PENDIENTE: str = (
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium "
    "bg-slate-100 text-slate-700 border border-slate-200"
)

BADGE_ESTADO_EN_PROGRESO: str = (
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium "
    "bg-amber-50 text-amber-800 border border-amber-200"
)

BADGE_ESTADO_EN_REVISION: str = (
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium "
    "bg-rose-50 text-rose-800 border border-rose-200"
)

BADGE_ESTADO_TERMINADA: str = (
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium "
    "bg-emerald-50 text-emerald-800 border border-emerald-200"
)

MAPA_CLASES_ESTADO_KANBAN: dict[EstadoKanban, str] = {
    EstadoKanban.PENDIENTE: BADGE_ESTADO_PENDIENTE,
    EstadoKanban.EN_PROGRESO: BADGE_ESTADO_EN_PROGRESO,
    EstadoKanban.EN_REVISION: BADGE_ESTADO_EN_REVISION,
    EstadoKanban.TERMINADA: BADGE_ESTADO_TERMINADA,
}


def obtenerClaseEstadoKanban(estado: EstadoKanban) -> str:
    """Retorna la clase Tailwind correspondiente al estado Kanban."""
    return MAPA_CLASES_ESTADO_KANBAN.get(estado, BADGE_ESTADO_PENDIENTE)


# ==============================================================================
# 10. BADGES DE ESTADO DERIVADO DE PAQUETE (EDT)
# ==============================================================================

BADGE_PAQUETE_SIN_TAREAS: str = (
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium "
    "bg-slate-100 text-slate-600 border border-slate-200"
)

BADGE_PAQUETE_PENDIENTE: str = (
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium "
    "bg-slate-100 text-slate-700 border border-slate-200"
)

BADGE_PAQUETE_EN_PROGRESO: str = (
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium "
    "bg-amber-50 text-amber-800 border border-amber-200"
)

BADGE_PAQUETE_TERMINADO: str = (
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium "
    "bg-emerald-50 text-emerald-800 border border-emerald-200"
)

MAPA_CLASES_ESTADO_PAQUETE: dict[EstadoPaquete, str] = {
    EstadoPaquete.SIN_TAREAS: BADGE_PAQUETE_SIN_TAREAS,
    EstadoPaquete.PENDIENTE: BADGE_PAQUETE_PENDIENTE,
    EstadoPaquete.EN_PROGRESO: BADGE_PAQUETE_EN_PROGRESO,
    EstadoPaquete.TERMINADO: BADGE_PAQUETE_TERMINADO,
}


def obtenerClaseEstadoPaquete(estado: EstadoPaquete) -> str:
    """Retorna la clase Tailwind correspondiente al estado derivado del paquete EDT."""
    return MAPA_CLASES_ESTADO_PAQUETE.get(estado, BADGE_PAQUETE_SIN_TAREAS)


# ==============================================================================
# 11. BADGE DE TAREA VENCIDA
# ==============================================================================

BADGE_TAREA_VENCIDA: str = (
    "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold "
    "bg-rose-100 text-rose-800 border border-rose-300"
)
