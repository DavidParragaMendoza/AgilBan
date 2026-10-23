"""Pruebas unitarias para catálogos y jerarquía inmutable de errores tipados."""

from dataclasses import FrozenInstanceError

import pytest

from app.domain.catalogos import (
    CargoIntegrante,
    EstadoKanban,
    EstadoPaquete,
    PrioridadTarea,
    TipoProyecto,
)
from app.domain.errores import (
    ErrorDominio,
    ErrorDuplicado,
    ErrorNoEncontrado,
    ErrorReglaNegocio,
    ErrorTransicionKanban,
    ErrorValidacion,
)


class TestCatalogosDominio:
    """Suite de pruebas para las enumeraciones de catálogo del dominio."""

    def testTipoProyectoValores(self) -> None:
        """Verifica los valores definidos para TipoProyecto."""
        esperados = {
            "Desarrollo Web",
            "Aplicación Móvil",
            "Ciencia de Datos / IA",
            "Infraestructura y Redes",
            "Marketing y Diseño",
            "Investigación Académica",
        }
        valores = {t.value for t in TipoProyecto}
        assert valores == esperados

    def testCargoIntegranteValores(self) -> None:
        """Verifica los valores definidos para CargoIntegrante."""
        esperados = {
            "Líder de Proyecto",
            "Desarrollador Backend",
            "Desarrollador Frontend",
            "Desarrollador Fullstack",
            "Ingeniero QA / Tester",
            "Diseñador UI/UX",
            "Analista de Datos",
        }
        valores = {c.value for c in CargoIntegrante}
        assert valores == esperados

    def testPrioridadTareaValores(self) -> None:
        """Verifica los 4 niveles de prioridad definidos."""
        esperados = {"Baja", "Media", "Alta", "Crítica"}
        valores = {p.value for p in PrioridadTarea}
        assert valores == esperados

    def testEstadoKanbanValores(self) -> None:
        """Verifica los 4 estados del tablero Kanban."""
        esperados = {"Pendiente", "En progreso", "En revisión", "Terminada"}
        valores = {e.value for e in EstadoKanban}
        assert valores == esperados

    def testEstadoPaqueteValores(self) -> None:
        """Verifica los 4 estados calculados para un paquete de trabajo."""
        esperados = {"Sin Tareas", "Pendiente", "En progreso", "Terminado"}
        valores = {e.value for e in EstadoPaquete}
        assert valores == esperados


class TestErroresDominioTipados:
    """Suite de pruebas para la jerarquía de errores de dominio inmutables."""

    def testJerarquiaYMensajeBase(self) -> None:
        """Verifica que todos los errores hereden de ErrorDominio y Exception."""
        err = ErrorValidacion(mensaje="Dato no válido", campo="titulo")
        assert isinstance(err, ErrorDominio)
        assert isinstance(err, Exception)
        assert str(err) == "Dato no válido"
        assert err.campo == "titulo"

    def testErrorDuplicadoAtributos(self) -> None:
        """Verifica atributos de ErrorDuplicado."""
        err = ErrorDuplicado(
            mensaje="Nombre ya existe",
            entidad="Proyecto",
            identificador="AgilBan Core",
        )
        assert err.entidad == "Proyecto"
        assert err.identificador == "AgilBan Core"

    def testErrorNoEncontradoAtributos(self) -> None:
        """Verifica atributos de ErrorNoEncontrado."""
        err = ErrorNoEncontrado(
            mensaje="Tarea inexistente",
            entidad="Tarea",
            identificador="TAR-999",
        )
        assert err.entidad == "Tarea"
        assert err.identificador == "TAR-999"

    def testErrorReglaNegocioAtributos(self) -> None:
        """Verifica atributos de ErrorReglaNegocio."""
        err = ErrorReglaNegocio(
            mensaje="No se puede eliminar paquete con tareas",
            codigo="PAQUETE_NO_VACIO",
        )
        assert err.codigo == "PAQUETE_NO_VACIO"

    def testErrorTransicionKanbanAtributos(self) -> None:
        """Verifica atributos de ErrorTransicionKanban."""
        err = ErrorTransicionKanban(
            mensaje="Salto inválido",
            origen=EstadoKanban.PENDIENTE,
            destino=EstadoKanban.TERMINADA,
        )
        assert err.origen == EstadoKanban.PENDIENTE
        assert err.destino == EstadoKanban.TERMINADA

    def testInmutabilidadErrores(self) -> None:
        """Verifica que mutar atributos lance FrozenInstanceError."""
        err = ErrorValidacion(mensaje="Longitud inválida", campo="cedula")
        with pytest.raises(FrozenInstanceError):
            err.campo = "nombre"  # type: ignore

    def testPatternMatchingErrores(self) -> None:
        """Comprueba el desempaquetado estructural exhaustivo con match/case."""

        def clasificarError(error: ErrorDominio) -> str:
            match error:
                case ErrorValidacion(m, c):
                    return f"Validacion({c}): {m}"
                case ErrorDuplicado(m, e, i):
                    return f"Duplicado({e}:{i}): {m}"
                case ErrorNoEncontrado(m, e, i):
                    return f"NoEncontrado({e}:{i}): {m}"
                case ErrorReglaNegocio(m, cod):
                    return f"ReglaNegocio({cod}): {m}"
                case ErrorTransicionKanban(m, o, d):
                    return f"Transicion({o.value}->{d.value}): {m}"
                case ErrorDominio(m):
                    return f"ErrorDominio: {m}"

        val = ErrorValidacion("Campo vacío", "descripcion")
        dup = ErrorDuplicado("Ya registrado", "Integrante", "0912345678")
        trn = ErrorTransicionKanban(
            "Ilegal",
            EstadoKanban.EN_PROGRESO,
            EstadoKanban.PENDIENTE,
        )

        assert clasificarError(val) == "Validacion(descripcion): Campo vacío"
        assert clasificarError(dup) == "Duplicado(Integrante:0912345678): Ya registrado"
        assert clasificarError(trn) == "Transicion(En progreso->Pendiente): Ilegal"
