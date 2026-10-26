"""Prueba de integración end-to-end del ciclo de vida completo de la Fase 1 (CLI).

Valida de extremo a extremo los requisitos funcionales RF-01 a RF-10 y RNF-01 a RNF-05:
- Creación de proyecto e inicialización relacional en SQLite.
- Evolución de la EDT y validación estricta de integrantes y paquetes.
- Alta, transiciones Kanban, devoluciones con justificación y borrado lógico de tareas.
- Panel de métricas cuantitativas, avance global, cuellos de botella y filtros analíticos.
- Integridad transaccional y ausencia de efectos colaterales.
"""

from __future__ import annotations

import sqlite3

from app.adapters.esquemaSqlite import inicializarEsquema
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
    calcularAvancePaquete,
    calcularEstadoPaquete,
    obtenerTareasActivas,
    renombrarPaquete,
)
from app.core.filtros import (
    crearCriterioFiltro,
    filtrarTareas,
    ordenarPorFecha,
    ordenarPorPrioridad,
)
from app.core.kanban import (
    avanzarOTareasKanban,
    descartarTareaLogicamente,
    esRetroceso,
    transicionesPermitidas,
)
from app.core.metricas import (
    auditarCuellosDeBotella,
    calcularAvanceGlobal,
    calcularCargaIntegrantes,
    calcularResumenTareas,
)
from app.core.validador import (
    validarCedula,
    validarEliminacionIntegrante,
    validarEliminacionPaquete,
    validarNombreIntegrante,
    validarNombrePaquete,
    validarNombreProyecto,
)
from app.domain.catalogos import (
    CargoIntegrante,
    EstadoKanban,
    EstadoPaquete,
    PrioridadTarea,
    TipoProyecto,
)
from app.domain.modelos import Integrante, PaqueteTrabajo, Proyecto, Tarea
from app.domain.monadas import Alguno, Exito, Fallo, Ninguno


def testCicloDeVidaCompletoFase1() -> None:
    """Ejecuta y verifica la secuencia completa de la Fase 1 en SQLite :memory:."""
    # 1. Inicialización de la base de datos (RF-10)
    con = sqlite3.connect(":memory:")
    resEsquema = inicializarEsquema(con)
    assert isinstance(resEsquema, Exito)

    # 2. Validación y creación del proyecto (RF-01)
    resNom = validarNombreProyecto("AgilBan Core", ())
    assert isinstance(resNom, Exito)

    resCedula = validarCedula("0912345678", ())
    assert isinstance(resCedula, Exito)

    resNomInt = validarNombreIntegrante("Deivy Prudente")
    assert isinstance(resNomInt, Exito)

    integLider = Integrante(
        cedula="0912345678",
        idProyecto="PROY-E2E",
        nombre="Deivy Prudente",
        cargo=CargoIntegrante.LIDER_PROYECTO,
    )
    paq1 = PaqueteTrabajo("PAQ-001", "PROY-E2E", "Arquitectura", ())
    proy = Proyecto(
        idProyecto="PROY-E2E",
        nombre="AgilBan Core",
        tipo=TipoProyecto.DESARROLLO_WEB,
        paquetes=(paq1,),
        integrantes=(integLider,),
    )
    resGuardar = guardarProyectoCompleto(con, proy)
    assert isinstance(resGuardar, Exito)

    # 3. Evolución de la EDT: Agregar y renombrar paquetes (RF-03)
    resValPaq = validarNombrePaquete("Backend", tuple(p.nombre for p in proy.paquetes))
    assert isinstance(resValPaq, Exito)
    paq2 = PaqueteTrabajo("PAQ-002", "PROY-E2E", "Backend", ())
    proy = agregarPaqueteAProyecto(proy, paq2)
    guardarProyectoCompleto(con, proy)

    resRenombrar = renombrarPaquete(proy, "PAQ-002", "Servicios Backend")
    assert isinstance(resRenombrar, Exito)
    proy = resRenombrar.valor
    actualizarNombrePaquete(con, "PAQ-002", "Servicios Backend")

    # 4. Gestión de Integrantes: Agregar segundo miembro (RF-02)
    integDev = Integrante(
        cedula="0987654321",
        idProyecto="PROY-E2E",
        nombre="Carlos Bernabe",
        cargo=CargoIntegrante.DESARROLLADOR_FULLSTACK,
    )
    proy = Proyecto(
        proy.idProyecto,
        proy.nombre,
        proy.tipo,
        proy.paquetes,
        proy.integrantes + (integDev,),
    )
    guardarProyectoCompleto(con, proy)

    # 5. Creación y asignación de tareas fijas en paquetes (RF-05)
    t1 = Tarea(
        idTarea="TAR-001",
        idPaquete="PAQ-001",
        titulo="Diseño del Functional Core",
        descripcion=Alguno("Separación estricta de pureza"),
        prioridad=PrioridadTarea.CRITICA,
        cedulaResponsable=Alguno("0912345678"),
        fechaObjetivo=Alguno("2026-11-01"),
        estado=EstadoKanban.PENDIENTE,
        contadorRegresos=0,
        activo=True,
        historial=(),
    )
    guardarTareaConHistorial(con, t1)

    t2 = Tarea(
        idTarea="TAR-002",
        idPaquete="PAQ-001",
        titulo="Modelos Inmutables",
        descripcion=Ninguno(),
        prioridad=PrioridadTarea.ALTA,
        cedulaResponsable=Alguno("0987654321"),
        fechaObjetivo=Alguno("2026-11-05"),
        estado=EstadoKanban.PENDIENTE,
        contadorRegresos=0,
        activo=True,
        historial=(),
    )
    guardarTareaConHistorial(con, t2)

    # 6. Cálculo derivado de la EDT (RF-04)
    proyRecup = recuperarProyectos(con).obtenerValor()[0]
    paq1Recup = proyRecup.paquetes[0]
    assert len(obtenerTareasActivas(paq1Recup)) == 2
    assert calcularEstadoPaquete(paq1Recup) == EstadoPaquete.PENDIENTE
    assert calcularAvancePaquete(paq1Recup) == 0.0

    # 7. Operación del Tablero Kanban: Avance secuencial legal (RF-06)
    transT1 = transicionesPermitidas(t1.estado)
    assert EstadoKanban.EN_PROGRESO in transT1
    assert not esRetroceso(t1.estado, EstadoKanban.EN_PROGRESO)

    resAvance1 = avanzarOTareasKanban(
        t1, EstadoKanban.EN_PROGRESO, Ninguno(), "2026-10-25T10:00:00"
    )
    assert isinstance(resAvance1, Exito)
    t1Modificada = resAvance1.valor
    guardarTareaConHistorial(con, t1Modificada)

    resAvance2 = avanzarOTareasKanban(
        t1Modificada, EstadoKanban.EN_REVISION, Ninguno(), "2026-10-25T11:00:00"
    )
    t1Modificada = resAvance2.obtenerValor()
    guardarTareaConHistorial(con, t1Modificada)

    # 8. Devolución / Retroceso obligatorio con justificación (RF-06)
    assert esRetroceso(t1Modificada.estado, EstadoKanban.EN_PROGRESO)
    # Intento de retroceso sin justificación (bloqueado)
    resFalloRetroceso = avanzarOTareasKanban(
        t1Modificada, EstadoKanban.EN_PROGRESO, Ninguno(), "2026-10-25T12:00:00"
    )
    assert isinstance(resFalloRetroceso, Fallo)

    # Retroceso con justificación válida
    resRetrocesoOk = avanzarOTareasKanban(
        t1Modificada,
        EstadoKanban.EN_PROGRESO,
        Alguno("Falta añadir validación de tipos inmutables"),
        "2026-10-25T12:00:00",
    )
    assert isinstance(resRetrocesoOk, Exito)
    t1ConRegreso = resRetrocesoOk.valor
    assert t1ConRegreso.contadorRegresos == 1
    guardarTareaConHistorial(con, t1ConRegreso)

    # Avanzar secuencialmente a En revisión y luego a Terminada
    resRevision = avanzarOTareasKanban(
        t1ConRegreso, EstadoKanban.EN_REVISION, Ninguno(), "2026-10-25T13:00:00"
    )
    t1EnRevision = resRevision.obtenerValor()
    guardarTareaConHistorial(con, t1EnRevision)

    resTerminar = avanzarOTareasKanban(
        t1EnRevision, EstadoKanban.TERMINADA, Ninguno(), "2026-10-25T14:00:00"
    )
    t1Terminada = resTerminar.obtenerValor()
    guardarTareaConHistorial(con, t1Terminada)

    # 9. Borrado lógico de tarea (RF-05)
    t2Descartada = descartarTareaLogicamente(t2)
    assert t2Descartada.activo is False
    guardarTareaConHistorial(con, t2Descartada)

    # 10. Consulta de Métricas, Cuellos de Botella y Filtros (RF-07, RF-08)
    proyFinal = recuperarProyectos(con).obtenerValor()[0]
    todasTareas = tuple(t for paq in proyFinal.paquetes for t in paq.tareas)

    resumen = calcularResumenTareas(todasTareas)
    assert resumen["totalActivas"] == 1  # Solo t1 activa
    assert resumen["totalInactivas"] == 1  # t2 descartada
    assert resumen[EstadoKanban.TERMINADA.value] == 1

    avanceGlobal = calcularAvanceGlobal(todasTareas)
    assert avanceGlobal == 100.0  # 1 de 1 activa terminada

    carga = calcularCargaIntegrantes(proyFinal.integrantes, todasTareas)
    assert carga["0912345678"]["asignadas"] == 1
    assert carga["0912345678"]["terminadas"] == 1

    cuellos = auditarCuellosDeBotella(todasTareas)
    assert len(cuellos) == 1
    assert cuellos[0].idTarea == "TAR-001"
    assert cuellos[0].contadorRegresos == 1

    # Filtros analíticos con closures y HOF
    criterioTerminadas = crearCriterioFiltro(
        estado=Alguno(EstadoKanban.TERMINADA),
        cedula=Ninguno(),
        prioridad=Ninguno(),
        soloVencidas=False,
        soloInactivas=False,
        fechaReferencia="2026-10-25",
    )
    filtradas = filtrarTareas(todasTareas, criterioTerminadas)
    assert len(filtradas) == 1
    assert filtradas[0].idTarea == "TAR-001"

    criterioInactivas = crearCriterioFiltro(
        estado=Ninguno(),
        cedula=Ninguno(),
        prioridad=Ninguno(),
        soloVencidas=False,
        soloInactivas=True,
        fechaReferencia="2026-10-25",
    )
    inactivasFiltradas = filtrarTareas(todasTareas, criterioInactivas)
    assert len(inactivasFiltradas) == 1
    assert inactivasFiltradas[0].idTarea == "TAR-002"

    ordenadasPrio = ordenarPorPrioridad(todasTareas)
    assert len(ordenadasPrio) == 2
    ordenadasFecha = ordenarPorFecha(todasTareas)
    assert len(ordenadasFecha) == 2

    # 11. Reglas de negocio de borrado restrictivo (RF-02, RF-03)
    # Bloqueo al eliminar paquete con tareas
    assert isinstance(validarEliminacionPaquete(paq1Recup), Fallo)
    # Éxito al eliminar paquete 2 que está vacío
    paq2Recup = proyFinal.paquetes[1]
    assert isinstance(validarEliminacionPaquete(paq2Recup), Exito)
    resElimPaq = eliminarPaqueteVacio(con, paq2Recup.idPaquete)
    assert isinstance(resElimPaq, Exito)

    # Bloqueo al eliminar integrante con tareas activas
    assert isinstance(
        validarEliminacionIntegrante("0912345678", proyFinal.integrantes, todasTareas),
        Fallo,
    )
    # Éxito al eliminar integrante sin tareas activas
    assert isinstance(
        validarEliminacionIntegrante("0987654321", proyFinal.integrantes, todasTareas),
        Exito,
    )
    resElimInt = eliminarIntegrante(con, "0987654321", proyFinal.idProyecto)
    assert isinstance(resElimInt, Exito)

    con.close()
