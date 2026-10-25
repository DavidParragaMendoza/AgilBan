# ruff: noqa: N999
"""Módulo del asistente interactivo para la creación guiada de proyectos en consola."""

import uuid
from collections.abc import Callable

from app.core.validador import (
    validarCedula,
    validarNombreIntegrante,
    validarNombrePaquete,
    validarNombreProyecto,
)
from app.domain.catalogos import CargoIntegrante, TipoProyecto
from app.domain.modelos import Integrante, PaqueteTrabajo, Proyecto
from app.domain.monadas import Exito, Fallo, Resultado


def generarIdDefectoProyecto() -> str:
    """Genera un identificador único por defecto para un nuevo proyecto."""
    return f"PROY-{uuid.uuid4().hex[:6].upper()}"


def generarIdDefectoPaquete(indice: int) -> str:
    """Genera un identificador por defecto para un paquete de trabajo."""
    return f"PAQ-{indice:03d}-{uuid.uuid4().hex[:4].upper()}"


def seleccionarTipoProyecto(
    lector: Callable[[str], str], emisor: Callable[[str], None]
) -> TipoProyecto | None:
    """Muestra el catálogo de tipos de proyecto y solicita la selección numérica."""
    tipos = list(TipoProyecto)
    while True:
        emisor("\nSeleccione el tipo de proyecto:")
        for idx, tipo in enumerate(tipos, 1):
            emisor(f"  {idx}. {tipo.value}")
        entrada = lector("Ingrese el número del tipo deseado (o 'cancelar'): ").strip()
        if entrada.lower() == "cancelar":
            return None
        if entrada.isdigit() and 1 <= int(entrada) <= len(tipos):
            return tipos[int(entrada) - 1]
        emisor(
            "⚠️  Opción no reconocida. Por favor, ingrese un número válido de la lista."
        )


def seleccionarCargoIntegrante(
    lector: Callable[[str], str], emisor: Callable[[str], None]
) -> CargoIntegrante | None:
    """Muestra el catálogo de cargos disponibles y solicita la selección numérica."""
    cargos = list(CargoIntegrante)
    while True:
        emisor("\nSeleccione el cargo del integrante:")
        for idx, cargo in enumerate(cargos, 1):
            emisor(f"  {idx}. {cargo.value}")
        entrada = lector("Ingrese el número del cargo (o 'cancelar'): ").strip()
        if entrada.lower() == "cancelar":
            return None
        if entrada.isdigit() and 1 <= int(entrada) <= len(cargos):
            return cargos[int(entrada) - 1]
        emisor(
            "⚠️  Opción no reconocida. Por favor, ingrese un número válido de la lista."
        )


def solicitarEnteroPositivo(
    mensaje: str,
    minimo: int,
    lector: Callable[[str], str],
    emisor: Callable[[str], None],
) -> int | None:
    """Solicita un número entero positivo mayor o igual a un mínimo dado."""
    while True:
        entrada = lector(mensaje).strip()
        if entrada.lower() == "cancelar":
            return None
        if entrada.isdigit() and int(entrada) >= minimo:
            return int(entrada)
        emisor(f"⚠️  Debe ingresar un número entero mayor o igual a {minimo}.")


def ejecutarAsistenteCreacionProyecto(
    nombresExistentes: tuple[str, ...],
    generadorIdProyecto: Callable[[], str] = generarIdDefectoProyecto,
    generadorIdPaquete: Callable[[int], str] = generarIdDefectoPaquete,
    lector: Callable[[str], str] = input,
    emisor: Callable[[str], None] = print,
) -> Resultado[Proyecto, str]:
    """Guía paso a paso al usuario en la creación interactiva de un proyecto válido."""
    emisor("\n" + "=" * 65)
    emisor("       ASISTENTE DE CREACIÓN DE PROYECTO — AGILBAN")
    emisor("=" * 65)
    emisor("(Escriba 'cancelar' en cualquier momento para abortar la creación)\n")

    # 1. Nombre del proyecto
    nombreProyecto = ""
    while True:
        entrada = lector("Ingrese el nombre del proyecto: ").strip()
        if entrada.lower() == "cancelar":
            return Fallo("Operación cancelada por el usuario.")
        validacion = validarNombreProyecto(entrada, nombresExistentes)
        match validacion:
            case Exito(nombreValido):
                nombreProyecto = nombreValido
                break
            case Fallo(err):
                emisor(f"⚠️  {err.mensaje}")

    # 2. Tipo de proyecto
    tipo = seleccionarTipoProyecto(lector, emisor)
    if tipo is None:
        return Fallo("Operación cancelada por el usuario.")

    idProyecto = generadorIdProyecto()

    # 3. Paquetes de trabajo iniciales
    emisor("\n--- Configuración de Paquetes de Trabajo (EDT) ---")
    cantPaquetes = solicitarEnteroPositivo(
        "¿Cuántos paquetes de trabajo iniciales desea registrar? (mínimo 1): ",
        1,
        lector,
        emisor,
    )
    if cantPaquetes is None:
        return Fallo("Operación cancelada por el usuario.")

    listaPaquetes: list[PaqueteTrabajo] = []
    nombresPaquetesExistentes: list[str] = []

    for idx in range(1, cantPaquetes + 1):
        while True:
            entrada = lector(f"Nombre del paquete #{idx}: ").strip()
            if entrada.lower() == "cancelar":
                return Fallo("Operación cancelada por el usuario.")
            valPaq = validarNombrePaquete(entrada, tuple(nombresPaquetesExistentes))
            match valPaq:
                case Exito(nombrePaqValido):
                    idPaquete = generadorIdPaquete(idx)
                    listaPaquetes.append(
                        PaqueteTrabajo(idPaquete, idProyecto, nombrePaqValido, ())
                    )
                    nombresPaquetesExistentes.append(nombrePaqValido)
                    break
                case Fallo(err):
                    emisor(f"⚠️  {err.mensaje}")

    # 4. Integrantes iniciales del equipo
    emisor("\n--- Configuración del Equipo de Integrantes ---")
    cantIntegrantes = solicitarEnteroPositivo(
        "¿Cuántos integrantes iniciales desea asignar al proyecto? (mínimo 1): ",
        1,
        lector,
        emisor,
    )
    if cantIntegrantes is None:
        return Fallo("Operación cancelada por el usuario.")

    listaIntegrantes: list[Integrante] = []
    cedulasRegistradas: list[str] = []

    for idx in range(1, cantIntegrantes + 1):
        emisor(f"\nDatos del integrante #{idx}:")
        # Cédula
        cedulaValida = ""
        while True:
            entradaCedula = lector("  Cédula de identidad (10 dígitos): ").strip()
            if entradaCedula.lower() == "cancelar":
                return Fallo("Operación cancelada por el usuario.")
            valCed = validarCedula(entradaCedula, tuple(cedulasRegistradas))
            match valCed:
                case Exito(ced):
                    cedulaValida = ced
                    cedulasRegistradas.append(ced)
                    break
                case Fallo(err):
                    emisor(f"  ⚠️  {err.mensaje}")

        # Nombre
        nombreValido = ""
        while True:
            entradaNombre = lector("  Nombre y apellido del integrante: ").strip()
            if entradaNombre.lower() == "cancelar":
                return Fallo("Operación cancelada por el usuario.")
            valNom = validarNombreIntegrante(entradaNombre)
            match valNom:
                case Exito(nom):
                    nombreValido = nom
                    break
                case Fallo(err):
                    emisor(f"  ⚠️  {err.mensaje}")

        # Cargo
        cargo = seleccionarCargoIntegrante(lector, emisor)
        if cargo is None:
            return Fallo("Operación cancelada por el usuario.")

        listaIntegrantes.append(
            Integrante(cedulaValida, idProyecto, nombreValido, cargo)
        )

    proyectoCreado = Proyecto(
        idProyecto=idProyecto,
        nombre=nombreProyecto,
        tipo=tipo,
        paquetes=tuple(listaPaquetes),
        integrantes=tuple(listaIntegrantes),
    )
    emisor("\n✅ ¡Proyecto configurado exitosamente con su EDT inicial y equipo!")
    return Exito(proyectoCreado)
