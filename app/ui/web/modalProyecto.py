# ruff: noqa: N999
"""Modal interactivo de creacion de proyecto con celdas dinamicas.

Implementa RF-01 y RF-02 (EARS-02.1 a EARS-02.5):
- Nombre de proyecto unico (max. 100 caracteres).
- Selector desplegable de TipoProyecto predefinido.
- Selector numerico de paquetes iniciales (minimo 1) con nombres por defecto "Paquete 1...N".
- Filas dinamicas reactivas para integrantes (cedula de 10 digitos, nombre alfabetico, cargo).
- Validacion en linea sin cerrar el modal ante errores de formato o duplicados.
- Persistencia valida con creacion inmutable y redireccion al Workspace.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from typing import Any

from reactpy import component, html, use_state
from reactpy.types import VdomDict

from app.core.validador import (
    validarCedula,
    validarNombreIntegrante,
    validarNombreProyecto,
)
from app.domain.catalogos import CargoIntegrante, TipoProyecto
from app.domain.modelos import Integrante, PaqueteTrabajo, Proyecto
from app.ui.web.estilos import (
    BOTON_PRIMARIO,
    BOTON_SECUNDARIO,
    CONTENEDOR_MODAL,
    CUERPO_MODAL,
    ENCABEZADO_MODAL,
    FONDO_MODAL_OVERLAY,
    INPUT_ERROR,
    INPUT_TEXTO,
    LABEL_FORMULARIO,
    PIE_MODAL,
    TEXTO_ERROR_FORMULARIO,
    TITULO_SECCION,
)

_PATRON_ID_PROYECTO = re.compile(r"^PROY-(\d+)$")


def generarIdProyectoSecuencial(proyectosExistentes: tuple[Proyecto, ...]) -> str:
    """Genera un identificador secuencial correlativo PROY-NNN basado en los proyectos existentes."""
    mayor = 0
    for p in proyectosExistentes:
        coincidencia = _PATRON_ID_PROYECTO.match(p.idProyecto)
        if coincidencia:
            mayor = max(mayor, int(coincidencia.group(1)))
    return (
        f"PROY-{mayor + 1:03d}" if mayor > 0 else f"PROY-{uuid.uuid4().hex[:6].upper()}"
    )


def validarFormularioProyecto(
    nombre: str,
    numPaquetes: int,
    integrantes: tuple[dict[str, str], ...],
    proyectosExistentes: tuple[Proyecto, ...],
) -> dict[str, str]:
    """Ejecuta puramente las validaciones del formulario retornando un mapa de errores por campo."""
    errores: dict[str, str] = {}

    # 1. Validar nombre del proyecto y unicidad
    nombresExistentes = tuple(p.nombre for p in proyectosExistentes)
    resNombre = validarNombreProyecto(nombre, nombresExistentes)
    if resNombre.esFallo():
        errores["nombre"] = resNombre.error.mensaje

    # 2. Validar cantidad minima de paquetes iniciales
    if numPaquetes < 1:
        errores["paquetes"] = "Debe registrar al menos un paquete de trabajo inicial."

    # 3. Validar integrantes
    if len(integrantes) < 1:
        errores["integrantes"] = (
            "Debe registrar al menos un integrante para conformar el equipo."
        )

    cedulasVistas: list[str] = []
    for i, integ in enumerate(integrantes):
        cedula = integ.get("cedula", "")
        nombreInteg = integ.get("nombre", "")

        resCedula = validarCedula(cedula, tuple(cedulasVistas))
        if resCedula.esFallo():
            errores[f"cedula_{i}"] = resCedula.error.mensaje
        else:
            cedulasVistas.append(resCedula.obtenerValor())

        resNombreInteg = validarNombreIntegrante(nombreInteg)
        if resNombreInteg.esFallo():
            errores[f"nombre_{i}"] = resNombreInteg.error.mensaje

    return errores


def construirEntidadProyecto(
    nombre: str,
    tipo: TipoProyecto,
    numPaquetes: int,
    integrantes: tuple[dict[str, str], ...],
    proyectosExistentes: tuple[Proyecto, ...],
) -> Proyecto:
    """Construye la entidad inmutable Proyecto con paquetes por defecto Paquete 1...N e integrantes."""
    idProyecto = generarIdProyectoSecuencial(proyectosExistentes)

    paquetes = tuple(
        PaqueteTrabajo(
            idPaquete=f"PAQ-{i + 1:03d}",
            idProyecto=idProyecto,
            nombre=f"Paquete {i + 1}",
            tareas=(),
        )
        for i in range(numPaquetes)
    )

    integrantesEntidades = tuple(
        Integrante(
            cedula=integ["cedula"].strip(),
            idProyecto=idProyecto,
            nombre=integ["nombre"].strip(),
            cargo=CargoIntegrante(integ["cargo"]),
        )
        for integ in integrantes
    )

    return Proyecto(
        idProyecto=idProyecto,
        nombre=nombre.strip(),
        tipo=tipo,
        paquetes=paquetes,
        integrantes=integrantesEntidades,
    )


def renderizarFilaIntegrante(
    indice: int,
    datos: dict[str, str],
    errores: dict[str, str],
    alActualizar: Callable[[int, str, str], None],
    alEliminar: Callable[[int], None],
    puedeEliminar: bool,
) -> VdomDict:
    """Renderiza puramente una celda dinamica de captura de datos de un integrante."""
    errorCedula = errores.get(f"cedula_{indice}")
    errorNombre = errores.get(f"nombre_{indice}")

    claseInputCedula = INPUT_ERROR if errorCedula else INPUT_TEXTO
    claseInputNombre = INPUT_ERROR if errorNombre else INPUT_TEXTO

    return html.div(
        {
            "id": f"fila-integrante-{indice}",
            "className": "p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2 relative group",
        },
        html.div(
            {"className": "grid grid-cols-1 md:grid-cols-12 gap-3 items-start"},
            # Cédula
            html.div(
                {"className": "md:col-span-3"},
                html.label(
                    {
                        "className": LABEL_FORMULARIO,
                        "htmlFor": f"input-cedula-{indice}",
                    },
                    "Cédula",
                ),
                html.input(
                    {
                        "id": f"input-cedula-{indice}",
                        "type": "text",
                        "maxLength": 10,
                        "placeholder": "10 dígitos…",
                        "value": datos.get("cedula", ""),
                        "onChange": lambda e: alActualizar(
                            indice, "cedula", e["target"]["value"]
                        ),
                        "className": claseInputCedula,
                    }
                ),
                (
                    html.span({"className": TEXTO_ERROR_FORMULARIO}, errorCedula)
                    if errorCedula
                    else html.div()
                ),
            ),
            # Nombre Completo
            html.div(
                {"className": "md:col-span-4"},
                html.label(
                    {
                        "className": LABEL_FORMULARIO,
                        "htmlFor": f"input-nombre-{indice}",
                    },
                    "Nombre",
                ),
                html.input(
                    {
                        "id": f"input-nombre-{indice}",
                        "type": "text",
                        "maxLength": 80,
                        "placeholder": "Nombre y apellido…",
                        "value": datos.get("nombre", ""),
                        "onChange": lambda e: alActualizar(
                            indice, "nombre", e["target"]["value"]
                        ),
                        "className": claseInputNombre,
                    }
                ),
                (
                    html.span({"className": TEXTO_ERROR_FORMULARIO}, errorNombre)
                    if errorNombre
                    else html.div()
                ),
            ),
            # Cargo
            html.div(
                {"className": "md:col-span-4"},
                html.label(
                    {
                        "className": LABEL_FORMULARIO,
                        "htmlFor": f"select-cargo-{indice}",
                    },
                    "Cargo",
                ),
                html.select(
                    {
                        "id": f"select-cargo-{indice}",
                        "value": datos.get(
                            "cargo", CargoIntegrante.LIDER_PROYECTO.value
                        ),
                        "onChange": lambda e: alActualizar(
                            indice, "cargo", e["target"]["value"]
                        ),
                        "className": f"{INPUT_TEXTO} bg-white",
                    },
                    *[
                        html.option({"value": cargo.value}, cargo.value)
                        for cargo in CargoIntegrante
                    ],
                ),
            ),
            # Botón quitar
            html.div(
                {"className": "md:col-span-1 pt-6 flex justify-center"},
                (
                    html.button(
                        {
                            "id": f"btn-eliminar-integrante-{indice}",
                            "type": "button",
                            "onClick": lambda e: alEliminar(indice),
                            "title": "Quitar integrante",
                            "className": "text-slate-400 hover:text-rose-600 font-bold text-base p-1",
                        },
                        "✕",
                    )
                    if puedeEliminar
                    else html.div()
                ),
            ),
        ),
    )


def renderizarModalCreacionProyecto(
    nombre: str,
    tipo: TipoProyecto,
    numPaquetes: int,
    integrantes: tuple[dict[str, str], ...],
    errores: dict[str, str],
    alCambiarNombre: Callable[[str], None],
    alCambiarTipo: Callable[[TipoProyecto], None],
    alCambiarPaquetes: Callable[[int], None],
    alActualizarIntegrante: Callable[[int, str, str], None],
    alAgregarIntegrante: Callable[[], None],
    alEliminarIntegrante: Callable[[int], None],
    alConfirmarGuardar: Callable[[], None],
    alCerrar: Callable[[], None],
) -> VdomDict:
    """Funcion pura de renderizado del dialogo modal con celdas dinamicas."""
    errorNombre = errores.get("nombre")
    errorPaquetes = errores.get("paquetes")
    errorIntegrantes = errores.get("integrantes")

    claseInputNombre = INPUT_ERROR if errorNombre else INPUT_TEXTO

    return html.div(
        {
            "id": "modal-creacion-proyecto-overlay",
            "className": FONDO_MODAL_OVERLAY,
        },
        html.div(
            {
                "id": "contenedor-modal-creacion",
                "className": f"{CONTENEDOR_MODAL} max-w-2xl",
            },
            # Encabezado
            html.div(
                {"className": ENCABEZADO_MODAL},
                html.div(
                    {"className": "space-y-0.5"},
                    html.h2({"className": TITULO_SECCION}, "Nuevo Proyecto AgilBan"),
                    html.p(
                        {"className": "text-xs text-slate-500"},
                        "Define la iniciativa y conforma el equipo inicial de trabajo.",
                    ),
                ),
                html.button(
                    {
                        "id": "btn-cerrar-modal-x",
                        "type": "button",
                        "onClick": lambda e: alCerrar(),
                        "className": "text-slate-400 hover:text-slate-600 text-lg font-bold p-1 focus:outline-none",
                    },
                    "✕",
                ),
            ),
            # Cuerpo de Formulario con Scroll
            html.div(
                {"className": CUERPO_MODAL},
                # Campo: Nombre del Proyecto
                html.div(
                    {"className": "space-y-1"},
                    html.label(
                        {
                            "className": LABEL_FORMULARIO,
                            "htmlFor": "input-nombre-proyecto",
                        },
                        "Nombre del Proyecto *",
                    ),
                    html.input(
                        {
                            "id": "input-nombre-proyecto",
                            "type": "text",
                            "maxLength": 100,
                            "placeholder": "Ej. Plataforma de Telemedicina…",
                            "value": nombre,
                            "onChange": lambda e: alCambiarNombre(e["target"]["value"]),
                            "className": claseInputNombre,
                        }
                    ),
                    (
                        html.span({"className": TEXTO_ERROR_FORMULARIO}, errorNombre)
                        if errorNombre
                        else html.div()
                    ),
                ),
                # Fila: Tipo de Proyecto y Cantidad de Paquetes Iniciales
                html.div(
                    {"className": "grid grid-cols-1 md:grid-cols-2 gap-4"},
                    # Tipo
                    html.div(
                        {"className": "space-y-1"},
                        html.label(
                            {
                                "className": LABEL_FORMULARIO,
                                "htmlFor": "select-tipo-proyecto",
                            },
                            "Tipo de Proyecto",
                        ),
                        html.select(
                            {
                                "id": "select-tipo-proyecto",
                                "value": tipo.value,
                                "onChange": lambda e: alCambiarTipo(
                                    TipoProyecto(e["target"]["value"])
                                ),
                                "className": f"{INPUT_TEXTO} bg-white",
                            },
                            *[
                                html.option({"value": t.value}, t.value)
                                for t in TipoProyecto
                            ],
                        ),
                    ),
                    # Paquetes Iniciales
                    html.div(
                        {"className": "space-y-1"},
                        html.label(
                            {
                                "className": LABEL_FORMULARIO,
                                "htmlFor": "input-cantidad-paquetes",
                            },
                            "Paquetes Iniciales (EDT)",
                        ),
                        html.input(
                            {
                                "id": "input-cantidad-paquetes",
                                "type": "number",
                                "min": 1,
                                "max": 20,
                                "value": str(numPaquetes),
                                "onChange": lambda e: alCambiarPaquetes(
                                    int(e["target"]["value"])
                                    if e["target"]["value"].isdigit()
                                    else 1
                                ),
                                "className": (
                                    INPUT_ERROR if errorPaquetes else INPUT_TEXTO
                                ),
                            }
                        ),
                        html.span(
                            {"className": "text-[11px] text-slate-400 block"},
                            "Nombres generados por defecto: Paquete 1...N (renombrables en barra lateral).",
                        ),
                        (
                            html.span(
                                {"className": TEXTO_ERROR_FORMULARIO},
                                errorPaquetes,
                            )
                            if errorPaquetes
                            else html.div()
                        ),
                    ),
                ),
                # Sección de Celdas Dinámicas: Integrantes del Equipo
                html.div(
                    {
                        "id": "seccion-integrantes-dinamicos",
                        "className": "space-y-3 pt-2",
                    },
                    html.div(
                        {"className": "flex items-center justify-between"},
                        html.label(
                            {"className": LABEL_FORMULARIO},
                            f"Integrantes del Equipo ({len(integrantes)}) *",
                        ),
                        html.button(
                            {
                                "id": "btn-agregar-fila-integrante",
                                "type": "button",
                                "onClick": lambda e: alAgregarIntegrante(),
                                "className": (
                                    "text-xs font-semibold text-indigo-600 hover:text-indigo-800 "
                                    "flex items-center space-x-1"
                                ),
                            },
                            "+ Agregar Integrante",
                        ),
                    ),
                    (
                        html.span(
                            {"className": TEXTO_ERROR_FORMULARIO},
                            errorIntegrantes,
                        )
                        if errorIntegrantes
                        else html.div()
                    ),
                    html.div(
                        {
                            "id": "contenedor-filas-integrantes",
                            "className": "space-y-2.5",
                        },
                        *[
                            renderizarFilaIntegrante(
                                indice=idx,
                                datos=integ,
                                errores=errores,
                                alActualizar=alActualizarIntegrante,
                                alEliminar=alEliminarIntegrante,
                                puedeEliminar=len(integrantes) > 1,
                            )
                            for idx, integ in enumerate(integrantes)
                        ],
                    ),
                ),
            ),
            # Pie con Botones de Acción
            html.div(
                {"className": PIE_MODAL},
                html.button(
                    {
                        "id": "btn-cancelar-modal",
                        "type": "button",
                        "onClick": lambda e: alCerrar(),
                        "className": BOTON_SECUNDARIO,
                    },
                    "Cancelar",
                ),
                html.button(
                    {
                        "id": "btn-guardar-proyecto-confirmar",
                        "type": "button",
                        "onClick": lambda e: alConfirmarGuardar(),
                        "className": BOTON_PRIMARIO,
                    },
                    "Guardar y Abrir Workspace",
                ),
            ),
        ),
    )


@component
def modalCreacionProyecto(
    alCerrar: Callable[[], None],
    alGuardar: Callable[[Proyecto], None],
    proyectosExistentes: tuple[Proyecto, ...] = (),
) -> Any:
    """Componente ReactPy del diálogo modal de creación con estado reactivo y celdas dinámicas."""
    nombre, setNombre = use_state("")
    tipo, setTipo = use_state(TipoProyecto.DESARROLLO_WEB)
    numPaquetes, setNumPaquetes = use_state(1)
    integrantes, setIntegrantes = use_state(
        (
            {
                "cedula": "",
                "nombre": "",
                "cargo": CargoIntegrante.LIDER_PROYECTO.value,
            },
        )
    )
    errores, setErrores = use_state(dict[str, str]())

    def actualizarIntegrante(indice: int, campo: str, valor: str) -> None:
        nuevos = list(integrantes)
        if 0 <= indice < len(nuevos):
            fila = dict(nuevos[indice])
            fila[campo] = valor
            nuevos[indice] = fila
            setIntegrantes(tuple(nuevos))

    def agregarIntegrante() -> None:
        setIntegrantes(
            integrantes
            + (
                {
                    "cedula": "",
                    "nombre": "",
                    "cargo": CargoIntegrante.DESARROLLADOR_FULLSTACK.value,
                },
            )
        )

    def eliminarIntegrante(indice: int) -> None:
        if len(integrantes) > 1 and 0 <= indice < len(integrantes):
            nuevos = tuple(integ for i, integ in enumerate(integrantes) if i != indice)
            setIntegrantes(nuevos)

    def confirmarGuardar() -> None:
        mapaErrores = validarFormularioProyecto(
            nombre=nombre,
            numPaquetes=numPaquetes,
            integrantes=integrantes,
            proyectosExistentes=proyectosExistentes,
        )
        if mapaErrores:
            setErrores(mapaErrores)
            return

        nuevoProyecto = construirEntidadProyecto(
            nombre=nombre,
            tipo=tipo,
            numPaquetes=numPaquetes,
            integrantes=integrantes,
            proyectosExistentes=proyectosExistentes,
        )
        alGuardar(nuevoProyecto)
        alCerrar()

    return renderizarModalCreacionProyecto(
        nombre=nombre,
        tipo=tipo,
        numPaquetes=numPaquetes,
        integrantes=integrantes,
        errores=errores,
        alCambiarNombre=setNombre,
        alCambiarTipo=setTipo,
        alCambiarPaquetes=setNumPaquetes,
        alActualizarIntegrante=actualizarIntegrante,
        alAgregarIntegrante=agregarIntegrante,
        alEliminarIntegrante=eliminarIntegrante,
        alConfirmarGuardar=confirmarGuardar,
        alCerrar=alCerrar,
    )
