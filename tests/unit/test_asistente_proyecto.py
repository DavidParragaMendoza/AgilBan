"""Pruebas unitarias para el asistente de creación de proyectos en consola."""

from collections.abc import Callable

from app.domain.catalogos import CargoIntegrante, TipoProyecto
from app.domain.modelos import Proyecto
from app.domain.monadas import Exito, Fallo
from app.ui.asistenteProyecto import ejecutarAsistenteCreacionProyecto


def crearLectorSimulado(respuestas: list[str]) -> Callable[[str], str]:
    """Genera una función lectora pura que consume una lista predeterminada de respuestas."""
    iterador = iter(respuestas)

    def lector(prompt: str) -> str:
        try:
            return next(iterador)
        except StopIteration:
            return ""

    return lector


def testAsistenteCreacionExitosa() -> None:
    """Verifica el flujo guiado completo para crear un proyecto válido."""
    entradas = [
        "Sistema de Gestión Hospitalaria",  # Nombre
        "1",  # Tipo: Desarrollo Web
        "2",  # Cantidad de paquetes iniciales
        "Arquitectura Backend",  # Nombre Paquete 1
        "Interfaz de Usuario",  # Nombre Paquete 2
        "2",  # Cantidad de integrantes iniciales
        "0955555555",  # Cédula 1
        "Javier Infante",  # Nombre 1
        "1",  # Cargo 1: Líder de Proyecto
        "0966666666",  # Cédula 2
        "Carlos Bernabe",  # Nombre 2
        "2",  # Cargo 2: Desarrollador Backend
    ]
    mensajesEmitidos: list[str] = []

    res = ejecutarAsistenteCreacionProyecto(
        nombresExistentes=(),
        generadorIdProyecto=lambda: "PROY-001",
        generadorIdPaquete=lambda idx: f"PAQ-00{idx}",
        lector=crearLectorSimulado(entradas),
        emisor=mensajesEmitidos.append,
    )

    assert isinstance(res, Exito)
    proyecto: Proyecto = res.valor
    assert proyecto.idProyecto == "PROY-001"
    assert proyecto.nombre == "Sistema de Gestión Hospitalaria"
    assert proyecto.tipo == TipoProyecto.DESARROLLO_WEB
    assert len(proyecto.paquetes) == 2
    assert proyecto.paquetes[0].nombre == "Arquitectura Backend"
    assert proyecto.paquetes[1].nombre == "Interfaz de Usuario"
    assert len(proyecto.integrantes) == 2
    assert proyecto.integrantes[0].cedula == "0955555555"
    assert proyecto.integrantes[0].nombre == "Javier Infante"
    assert proyecto.integrantes[0].cargo == CargoIntegrante.LIDER_PROYECTO
    assert proyecto.integrantes[1].cedula == "0966666666"


def testAsistenteReintentaNombreDuplicadoYVacio() -> None:
    """Verifica que el asistente solicite reintento ante nombres vacíos o duplicados."""
    entradas = [
        "",  # Nombre vacío -> error
        "Proyecto Existente",  # Nombre duplicado -> error
        "Proyecto Nuevo y Valido",  # Nombre válido
        "2",  # Tipo: Aplicación Móvil
        "1",  # 1 paquete
        "Modulo Principal",
        "1",  # 1 integrante
        "0911111111",
        "Ana Maria",
        "3",  # Desarrollador Frontend
    ]
    mensajes: list[str] = []

    res = ejecutarAsistenteCreacionProyecto(
        nombresExistentes=("proyecto existente",),
        generadorIdProyecto=lambda: "PROY-002",
        generadorIdPaquete=lambda idx: f"PAQ-00{idx}",
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert isinstance(res, Exito)
    assert res.valor.nombre == "Proyecto Nuevo y Valido"
    assert any("Ya existe" in m or "duplicado" in m.lower() for m in mensajes)


def testAsistenteReintentaCedulaInvalidaYDuplicada() -> None:
    """Verifica que el asistente no permita registrar cédulas inválidas o duplicadas en el mismo proyecto."""
    entradas = [
        "Proyecto Movil",
        "2",  # Móvil
        "1",  # 1 paquete
        "Core App",
        "2",  # 2 integrantes
        "123",  # Cédula inválida (no tiene 10 dígitos)
        "0987654321",  # Cédula 1 válida
        "David Mendoza",
        "4",  # Cargo 4
        "0987654321",  # Cédula 2 duplicada de la 1
        "0988888888",  # Cédula 2 válida
        "Deivy Prudente",
        "5",  # Cargo 5
    ]
    mensajes: list[str] = []

    res = ejecutarAsistenteCreacionProyecto(
        nombresExistentes=(),
        generadorIdProyecto=lambda: "PROY-003",
        generadorIdPaquete=lambda idx: f"PAQ-00{idx}",
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert isinstance(res, Exito)
    assert len(res.valor.integrantes) == 2
    assert res.valor.integrantes[0].cedula == "0987654321"
    assert res.valor.integrantes[1].cedula == "0988888888"


def testAsistenteCancelar() -> None:
    """Verifica que el usuario pueda cancelar la creación escribiendo 'cancelar'."""
    entradas = ["cancelar"]
    mensajes: list[str] = []

    res = ejecutarAsistenteCreacionProyecto(
        nombresExistentes=(),
        generadorIdProyecto=lambda: "PROY-004",
        generadorIdPaquete=lambda idx: f"PAQ-00{idx}",
        lector=crearLectorSimulado(entradas),
        emisor=mensajes.append,
    )

    assert isinstance(res, Fallo)
    assert "cancelada" in res.error.lower()
