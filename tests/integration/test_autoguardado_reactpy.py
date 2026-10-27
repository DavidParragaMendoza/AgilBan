"""Pruebas de integración para autoguardado, persistencia reactiva y transiciones en AgilBan (Fase 2).

Valida de extremo a extremo los requisitos IT-AUT-01 a IT-AUT-06 y RNF-03:
- IT-AUT-01: Autoguardado on_blur de título (1 a 120 caracteres) persistido en SQLite.
- IT-AUT-02: Validación de título vacío o solo espacios bloquea persistencia y muestra error.
- IT-AUT-03: Autoguardado on_change de responsable asignando cédula a integrante válido en SQLite.
- IT-AUT-04: Autoguardado on_change a 'Sin asignar' actualiza a NULL en base de datos.
- IT-AUT-05: Descarte lógico desde Side Drawer actualiza activo = 0 en SQLite y retira la tarjeta del Kanban activo.
- IT-AUT-06: Flujo completo de devolución con justificación obligatoria incrementando contador_regresos en +1 e insertando en historial_transiciones.
"""

from __future__ import annotations

import asyncio
import sqlite3
from typing import Any

from reactpy.core.layout import Layout

from app.adapters.esquemaSqlite import inicializarEsquema
from app.adapters.repositorioSqlite import (
    guardarProyectoCompleto,
)
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
)
from app.domain.monadas import Alguno, Ninguno
from app.ui.web.app import componenteApp


def _buscarPorId(vdom: Any, elementoId: str) -> Any:
    """Busca recursivamente un nodo VDOM por su identificador 'id'."""
    if isinstance(vdom, dict):
        atributos = vdom.get("attributes", {})
        if atributos.get("id") == elementoId:
            return vdom
        for hijo in vdom.get("children", []):
            encontrado = _buscarPorId(hijo, elementoId)
            if encontrado is not None:
                return encontrado
    elif isinstance(vdom, (list, tuple)):
        for item in vdom:
            encontrado = _buscarPorId(item, elementoId)
            if encontrado is not None:
                return encontrado
    return None


def _contieneTexto(vdom: Any, texto: str) -> bool:
    """Verifica si un fragmento de texto aparece en cualquier nodo del VDOM."""
    if isinstance(vdom, str):
        return texto in vdom
    if isinstance(vdom, dict):
        for hijo in vdom.get("children", []):
            if _contieneTexto(hijo, texto):
                return True
    elif isinstance(vdom, (list, tuple)):
        for item in vdom:
            if _contieneTexto(item, texto):
                return True
    return False


def _crearEntornoPrueba(
    idProyecto: str = "PROY-INT",
    idPaquete: str = "PAQ-INT",
    tareas: tuple[Tarea, ...] = (),
    integrantes: tuple[Integrante, ...] = (),
) -> tuple[sqlite3.Connection, Proyecto]:
    """Crea una base de datos SQLite en memoria con esquema y un proyecto inicializado."""
    conexion = sqlite3.connect(":memory:")
    inicializarEsquema(conexion)

    paquete = PaqueteTrabajo(
        idPaquete=idPaquete,
        idProyecto=idProyecto,
        nombre="Módulo de Integración",
        tareas=tareas,
    )
    proyecto = Proyecto(
        idProyecto=idProyecto,
        nombre="Proyecto Integración E2E",
        tipo=TipoProyecto.DESARROLLO_WEB,
        paquetes=(paquete,),
        integrantes=integrantes,
    )
    guardarProyectoCompleto(conexion, proyecto)
    return conexion, proyecto


class TestAutoguardadoReactPyIntegracion:
    """Suite de integración end-to-end de autoguardado, descarte y devoluciones sobre SQLite."""

    def testIT_AUT_01_AutoguardadoOnBlurTituloPersisteEnSQLite(self) -> None:
        """Verifica IT-AUT-01: Autoguardado on_blur de título (1-120 caracteres) persistido en SQLite."""
        tareaInicial = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-INT",
            titulo="Título Original",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.PENDIENTE,
            activo=True,
        )
        conexion, _ = _crearEntornoPrueba(tareas=(tareaInicial,))

        async def flujo() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                u0 = await layout.render()
                # 1. Navegar a Workspace
                btnWs = _buscarPorId(u0["model"], "nav-item-workspace")
                assert btnWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uWs = await layout.render()

                # 2. Abrir Drawer de edición al hacer clic en la tarjeta
                tarjeta = _buscarPorId(uWs["model"], "titulo-tarea-TAR-001")
                assert tarjeta is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": tarjeta["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uDrawer = await layout.render()
                assert (
                    _buscarPorId(uDrawer["model"], "panel-edicion-tarea-drawer")
                    is not None
                )

                # 3. Modificar título y disparar evento onBlur con render intermedio
                inputTitulo = _buscarPorId(
                    uDrawer["model"], "input-titulo-tarea-drawer"
                )
                assert inputTitulo is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputTitulo["eventHandlers"]["onChange"]["target"],
                        "data": [{"target": {"value": "Título Persistido en SQLite"}}],
                    }
                )
                uDrawer2 = await layout.render()
                inputTitulo2 = _buscarPorId(
                    uDrawer2["model"], "input-titulo-tarea-drawer"
                )
                assert inputTitulo2 is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputTitulo2["eventHandlers"]["onBlur"]["target"],
                        "data": [{}],
                    }
                )
                uGuardado = await layout.render()
                assert _contieneTexto(uGuardado["model"], "✓ Guardado")

        asyncio.run(flujo())

        # Verificación directa en base de datos relacional
        cursor = conexion.cursor()
        cursor.execute("SELECT titulo FROM tareas WHERE id_tarea = ?", ("TAR-001",))
        fila = cursor.fetchone()
        assert fila is not None
        assert fila[0] == "Título Persistido en SQLite"

    def testIT_AUT_02_ValidacionTituloVacioBloqueaPersistenciaYMuestraError(
        self,
    ) -> None:
        """Verifica IT-AUT-02: Validación de título vacío o solo espacios bloquea persistencia y muestra error."""
        tareaInicial = Tarea(
            idTarea="TAR-002",
            idPaquete="PAQ-INT",
            titulo="Título Valido Original",
            prioridad=PrioridadTarea.ALTA,
            estado=EstadoKanban.PENDIENTE,
            activo=True,
        )
        conexion, _ = _crearEntornoPrueba(tareas=(tareaInicial,))

        async def flujo() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                u0 = await layout.render()
                btnWs = _buscarPorId(u0["model"], "nav-item-workspace")
                assert btnWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uWs = await layout.render()

                tarjeta = _buscarPorId(uWs["model"], "titulo-tarea-TAR-002")
                assert tarjeta is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": tarjeta["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uDrawer = await layout.render()

                # Modificar título a solo espacios y disparar onBlur
                inputTitulo = _buscarPorId(
                    uDrawer["model"], "input-titulo-tarea-drawer"
                )
                assert inputTitulo is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputTitulo["eventHandlers"]["onChange"]["target"],
                        "data": [{"target": {"value": "    "}}],
                    }
                )
                uDrawer2 = await layout.render()
                inputTitulo2 = _buscarPorId(
                    uDrawer2["model"], "input-titulo-tarea-drawer"
                )
                assert inputTitulo2 is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputTitulo2["eventHandlers"]["onBlur"]["target"],
                        "data": [{}],
                    }
                )
                uError = await layout.render()
                errElem = _buscarPorId(uError["model"], "error-titulo-tarea-drawer")
                assert errElem is not None
                assert (
                    "El título es obligatorio y debe tener entre 1 y 120 caracteres"
                    in errElem["children"][0]
                )

        asyncio.run(flujo())

        # Verificar que en SQLite se mantuvo inalterado el título original
        cursor = conexion.cursor()
        cursor.execute("SELECT titulo FROM tareas WHERE id_tarea = ?", ("TAR-002",))
        fila = cursor.fetchone()
        assert fila is not None
        assert fila[0] == "Título Valido Original"

    def testIT_AUT_03_AutoguardadoOnChangeResponsableAsignaCedulaAIntegranteValido(
        self,
    ) -> None:
        """Verifica IT-AUT-03: Autoguardado on_change de responsable asignando cédula a integrante válido en SQLite."""
        integrante = Integrante(
            cedula="0922334455",
            idProyecto="PROY-INT",
            nombre="Carlos Bernabe",
            cargo=CargoIntegrante.DESARROLLADOR_FRONTEND,
        )
        tareaInicial = Tarea(
            idTarea="TAR-003",
            idPaquete="PAQ-INT",
            titulo="Tarea Sin Asignar",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.PENDIENTE,
            cedulaResponsable=Ninguno(),
            activo=True,
        )
        conexion, _ = _crearEntornoPrueba(
            tareas=(tareaInicial,),
            integrantes=(integrante,),
        )

        async def flujo() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                u0 = await layout.render()
                btnWs = _buscarPorId(u0["model"], "nav-item-workspace")
                assert btnWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uWs = await layout.render()

                tarjeta = _buscarPorId(uWs["model"], "titulo-tarea-TAR-003")
                assert tarjeta is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": tarjeta["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uDrawer = await layout.render()

                # Asignar integrante mediante onChange
                selectResp = _buscarPorId(
                    uDrawer["model"], "select-responsable-tarea-drawer"
                )
                assert selectResp is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": selectResp["eventHandlers"]["onChange"]["target"],
                        "data": [{"target": {"value": "0922334455"}}],
                    }
                )
                uPost = await layout.render()
                assert _contieneTexto(uPost["model"], "✓ Guardado")

        asyncio.run(flujo())

        # Verificar en SQLite que cedula_responsable se guardó correctamente
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT cedula_responsable FROM tareas WHERE id_tarea = ?", ("TAR-003",)
        )
        fila = cursor.fetchone()
        assert fila is not None
        assert fila[0] == "0922334455"

    def testIT_AUT_04_AutoguardadoOnChangeSinAsignarActualizaANullEnBaseDatos(
        self,
    ) -> None:
        """Verifica IT-AUT-04: Autoguardado on_change a 'Sin asignar' actualiza a NULL en base de datos."""
        integrante = Integrante(
            cedula="0922334455",
            idProyecto="PROY-INT",
            nombre="Carlos Bernabe",
            cargo=CargoIntegrante.DESARROLLADOR_FRONTEND,
        )
        tareaInicial = Tarea(
            idTarea="TAR-004",
            idPaquete="PAQ-INT",
            titulo="Tarea Con Asignacion",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.PENDIENTE,
            cedulaResponsable=Alguno("0922334455"),
            activo=True,
        )
        conexion, _ = _crearEntornoPrueba(
            tareas=(tareaInicial,),
            integrantes=(integrante,),
        )

        async def flujo() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                u0 = await layout.render()
                btnWs = _buscarPorId(u0["model"], "nav-item-workspace")
                assert btnWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uWs = await layout.render()

                tarjeta = _buscarPorId(uWs["model"], "titulo-tarea-TAR-004")
                assert tarjeta is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": tarjeta["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uDrawer = await layout.render()

                # Cambiar a 'Sin asignar' (valor vacio)
                selectResp = _buscarPorId(
                    uDrawer["model"], "select-responsable-tarea-drawer"
                )
                assert selectResp is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": selectResp["eventHandlers"]["onChange"]["target"],
                        "data": [{"target": {"value": ""}}],
                    }
                )
                uPost = await layout.render()
                assert _contieneTexto(uPost["model"], "✓ Guardado")

        asyncio.run(flujo())

        # Verificar en SQLite que cedula_responsable es NULL (None en Python)
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT cedula_responsable FROM tareas WHERE id_tarea = ?", ("TAR-004",)
        )
        fila = cursor.fetchone()
        assert fila is not None
        assert fila[0] is None

    def testIT_AUT_05_DescarteLogicoDesdeDrawerActualizaActivoCeroYRetiraDelKanbanActivo(
        self,
    ) -> None:
        """Verifica IT-AUT-05: Descarte lógico desde Side Drawer actualiza activo = 0 en SQLite y retira la tarjeta."""
        tareaInicial = Tarea(
            idTarea="TAR-005",
            idPaquete="PAQ-INT",
            titulo="Tarea A Descartar",
            prioridad=PrioridadTarea.BAJA,
            estado=EstadoKanban.PENDIENTE,
            activo=True,
        )
        conexion, _ = _crearEntornoPrueba(tareas=(tareaInicial,))

        async def flujo() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                u0 = await layout.render()
                btnWs = _buscarPorId(u0["model"], "nav-item-workspace")
                assert btnWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uWs = await layout.render()

                # Abrir drawer
                tarjeta = _buscarPorId(uWs["model"], "titulo-tarea-TAR-005")
                assert tarjeta is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": tarjeta["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uDrawer = await layout.render()

                # Clic en Descartar Tarea
                btnDescartar = _buscarPorId(uDrawer["model"], "btn-descartar-tarea")
                assert btnDescartar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnDescartar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uConf = await layout.render()
                assert (
                    _buscarPorId(uConf["model"], "confirmacion-descarte-tarea")
                    is not None
                )

                # Confirmar Descarte
                btnConfirmar = _buscarPorId(
                    uConf["model"], "btn-confirmar-descarte-tarea"
                )
                assert btnConfirmar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnConfirmar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uFinal = await layout.render()

                # La tarjeta ya no está presente en el tablero Kanban
                assert _buscarPorId(uFinal["model"], "tarjeta-kanban-TAR-005") is None

        asyncio.run(flujo())

        # Verificar en SQLite que activo = 0
        cursor = conexion.cursor()
        cursor.execute("SELECT activo FROM tareas WHERE id_tarea = ?", ("TAR-005",))
        fila = cursor.fetchone()
        assert fila is not None
        assert fila[0] == 0

    def testIT_AUT_06_FlujoCompletoDevolucionConJustificacionIncrementaContadorRegresosEInsertaHistorial(
        self,
    ) -> None:
        """Verifica IT-AUT-06: Devolución con justificación obligatoria incrementa contador_regresos en +1 e inserta historial."""
        tareaInicial = Tarea(
            idTarea="TAR-006",
            idPaquete="PAQ-INT",
            titulo="Tarea Para Devolución",
            prioridad=PrioridadTarea.CRITICA,
            estado=EstadoKanban.EN_PROGRESO,
            contadorRegresos=0,
            activo=True,
        )
        conexion, _ = _crearEntornoPrueba(tareas=(tareaInicial,))

        async def flujo() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                u0 = await layout.render()
                btnWs = _buscarPorId(u0["model"], "nav-item-workspace")
                assert btnWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uWs = await layout.render()

                # Clic en botón devolver de la tarjeta
                btnDevolver = _buscarPorId(uWs["model"], "btn-devolver-tarea-TAR-006")
                assert btnDevolver is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnDevolver["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uModal = await layout.render()
                assert (
                    _buscarPorId(uModal["model"], "modal-regreso-dialogo") is not None
                )

                # Ingresar motivo de devolución obligatorio con render reactivo
                inputMotivo = _buscarPorId(uModal["model"], "input-motivo-regreso")
                assert inputMotivo is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputMotivo["eventHandlers"]["onChange"]["target"],
                        "data": [
                            {
                                "target": {
                                    "value": "Rechazado en pruebas de integración por regresión de UI"
                                }
                            }
                        ],
                    }
                )
                uModal2 = await layout.render()
                btnConfirmar = _buscarPorId(uModal2["model"], "btn-confirmar-regreso")
                assert btnConfirmar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnConfirmar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uFinal = await layout.render()
                # El modal se cierra tras la confirmación exitosa
                assert _buscarPorId(uFinal["model"], "modal-regreso-dialogo") is None

        asyncio.run(flujo())

        # Verificar en SQLite: estado = PENDIENTE, contador_regresos = 1
        cursor = conexion.cursor()
        cursor.execute(
            "SELECT estado, contador_regresos FROM tareas WHERE id_tarea = ?",
            ("TAR-006",),
        )
        fila = cursor.fetchone()
        assert fila is not None
        assert fila[0] == EstadoKanban.PENDIENTE.value
        assert fila[1] == 1

        # Verificar inserción en tabla historial_transiciones
        cursor.execute(
            "SELECT estado_origen, estado_destino, comentario FROM historial_transiciones WHERE id_tarea = ?",
            ("TAR-006",),
        )
        filasHist = cursor.fetchall()
        assert len(filasHist) == 1
        assert filasHist[0][0] == EstadoKanban.EN_PROGRESO.value
        assert filasHist[0][1] == EstadoKanban.PENDIENTE.value
        assert (
            filasHist[0][2] == "Rechazado en pruebas de integración por regresión de UI"
        )

    def testIT_AUT_07_AutoguardadoOnChangePrioridadPersisteEnSQLite(self) -> None:
        """Verifica que el cambio reactivo de prioridad persista inmediatamente en SQLite."""
        tareaInicial = Tarea(
            idTarea="TAR-007",
            idPaquete="PAQ-INT",
            titulo="Tarea Cambio Prioridad",
            prioridad=PrioridadTarea.BAJA,
            estado=EstadoKanban.PENDIENTE,
            activo=True,
        )
        conexion, _ = _crearEntornoPrueba(tareas=(tareaInicial,))

        async def flujo() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                u0 = await layout.render()
                btnWs = _buscarPorId(u0["model"], "nav-item-workspace")
                assert btnWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uWs = await layout.render()

                tarjeta = _buscarPorId(uWs["model"], "titulo-tarea-TAR-007")
                assert tarjeta is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": tarjeta["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uDrawer = await layout.render()

                selectPrio = _buscarPorId(
                    uDrawer["model"], "select-prioridad-tarea-drawer"
                )
                assert selectPrio is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": selectPrio["eventHandlers"]["onChange"]["target"],
                        "data": [{"target": {"value": PrioridadTarea.CRITICA.value}}],
                    }
                )
                uPost = await layout.render()
                assert _contieneTexto(uPost["model"], "✓ Guardado")

        asyncio.run(flujo())

        cursor = conexion.cursor()
        cursor.execute("SELECT prioridad FROM tareas WHERE id_tarea = ?", ("TAR-007",))
        fila = cursor.fetchone()
        assert fila is not None
        assert fila[0] == PrioridadTarea.CRITICA.value

    def testIT_AUT_08_AltaTransaccionalConClaveIdempotenteYAperturaDrawer(self) -> None:
        """Verifica la creación reactiva de tarea con clave idempotente, persistencia en SQLite y apertura de drawer."""
        conexion, _ = _crearEntornoPrueba(tareas=())

        async def flujo() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                u0 = await layout.render()
                btnWs = _buscarPorId(u0["model"], "nav-item-workspace")
                assert btnWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uWs = await layout.render()

                # Clic en Crear primera tarea del paquete vacío
                btnCrear = _buscarPorId(uWs["model"], "btn-crear-primera-tarea")
                assert btnCrear is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnCrear["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uModal = await layout.render()
                assert _buscarPorId(uModal["model"], "modal-nueva-tarea") is not None

                # Ingresar título válido y renderizar
                inputTit = _buscarPorId(uModal["model"], "input-titulo-nueva-tarea")
                assert inputTit is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputTit["eventHandlers"]["onChange"]["target"],
                        "data": [
                            {"target": {"value": "Nueva Tarea Alta Transaccional"}}
                        ],
                    }
                )
                uModal2 = await layout.render()
                btnGuardar = _buscarPorId(uModal2["model"], "btn-guardar-nueva-tarea")
                assert btnGuardar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnGuardar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uPost = await layout.render()
                # Tras el alta exitosa, el drawer de edición se abre automáticamente
                assert (
                    _buscarPorId(uPost["model"], "panel-edicion-tarea-drawer")
                    is not None
                )

        asyncio.run(flujo())

        # Verificar en SQLite que la tarea fue creada y tiene evento de creación en historial_creaciones
        cursor = conexion.cursor()
        cursor.execute("SELECT id_tarea, titulo, estado, activo FROM tareas")
        tareas = cursor.fetchall()
        assert len(tareas) == 1
        idTarea, titulo, estado, activo = tareas[0]
        assert titulo == "Nueva Tarea Alta Transaccional"
        assert estado == EstadoKanban.PENDIENTE.value
        assert activo == 1

        cursor.execute(
            "SELECT id_tarea, fecha_hora, clave_solicitud FROM historial_creaciones WHERE id_tarea = ?",
            (idTarea,),
        )
        evCreacion = cursor.fetchone()
        assert evCreacion is not None
        assert evCreacion[0] == idTarea
        assert len(evCreacion[2]) > 0

    def testIT_AUT_09_ProteccionCierreDrawerConBorradorPendienteYDescarteManual(
        self,
    ) -> None:
        """Verifica que un borrador modificado sin guardar bloquee el cierre hasta confirmación explícita."""
        tareaInicial = Tarea(
            idTarea="TAR-009",
            idPaquete="PAQ-INT",
            titulo="Título Estable",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.PENDIENTE,
            activo=True,
        )
        conexion, _ = _crearEntornoPrueba(tareas=(tareaInicial,))

        async def flujo() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                u0 = await layout.render()
                btnWs = _buscarPorId(u0["model"], "nav-item-workspace")
                assert btnWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uWs = await layout.render()

                tarjeta = _buscarPorId(uWs["model"], "titulo-tarea-TAR-009")
                assert tarjeta is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": tarjeta["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uDrawer = await layout.render()

                # Modificar título y renderizar (borrador pendiente)
                inputTit = _buscarPorId(uDrawer["model"], "input-titulo-tarea-drawer")
                assert inputTit is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputTit["eventHandlers"]["onChange"]["target"],
                        "data": [{"target": {"value": "Borrador Incompleto"}}],
                    }
                )
                uDrawer2 = await layout.render()

                # Intentar cerrar el drawer mediante la 'X'
                btnCerrar = _buscarPorId(uDrawer2["model"], "btn-cerrar-drawer-tarea")
                assert btnCerrar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnCerrar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uAdv = await layout.render()
                # Debe mostrar diálogo de advertencia de borrador
                assert (
                    _buscarPorId(uAdv["model"], "advertencia-cierre-drawer") is not None
                )

                # Confirmar descarte del borrador y cierre
                btnDescartarBorrador = _buscarPorId(
                    uAdv["model"], "btn-descartar-borrador-cerrar"
                )
                assert btnDescartarBorrador is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnDescartarBorrador["eventHandlers"]["onClick"][
                            "target"
                        ],
                        "data": [{}],
                    }
                )
                # Primer render procesa estado local del drawer, segundo render procesa desmonte en app
                await layout.render()
                uFinal = await layout.render()
                # Drawer cerrado
                assert (
                    _buscarPorId(uFinal["model"], "panel-edicion-tarea-drawer") is None
                )

        asyncio.run(flujo())

        # En base de datos el título sigue siendo el original
        cursor = conexion.cursor()
        cursor.execute("SELECT titulo FROM tareas WHERE id_tarea = ?", ("TAR-009",))
        fila = cursor.fetchone()
        assert fila is not None
        assert fila[0] == "Título Estable"

    def testIT_AUT_10_CancelacionDescarteLogicoPreservaTareaEnKanbanYBaseDatos(
        self,
    ) -> None:
        """Verifica que cancelar el diálogo de descarte lógico preserve la tarea tanto en UI como en SQLite."""
        tareaInicial = Tarea(
            idTarea="TAR-010",
            idPaquete="PAQ-INT",
            titulo="Tarea A Conservar",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.PENDIENTE,
            activo=True,
        )
        conexion, _ = _crearEntornoPrueba(tareas=(tareaInicial,))

        async def flujo() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                u0 = await layout.render()
                btnWs = _buscarPorId(u0["model"], "nav-item-workspace")
                assert btnWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uWs = await layout.render()

                tarjeta = _buscarPorId(uWs["model"], "titulo-tarea-TAR-010")
                assert tarjeta is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": tarjeta["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uDrawer = await layout.render()

                btnDescartar = _buscarPorId(uDrawer["model"], "btn-descartar-tarea")
                assert btnDescartar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnDescartar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uConf = await layout.render()
                assert (
                    _buscarPorId(uConf["model"], "confirmacion-descarte-tarea")
                    is not None
                )

                # Cancelar descarte
                btnCancelar = _buscarPorId(
                    uConf["model"], "btn-cancelar-descarte-tarea"
                )
                assert btnCancelar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnCancelar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                uPostCancel = await layout.render()
                # Diálogo de confirmación desaparece
                assert (
                    _buscarPorId(uPostCancel["model"], "confirmacion-descarte-tarea")
                    is None
                )
                # Drawer sigue abierto con la tarea
                assert (
                    _buscarPorId(uPostCancel["model"], "panel-edicion-tarea-drawer")
                    is not None
                )

        asyncio.run(flujo())

        # En base de datos la tarea sigue activa (activo = 1)
        cursor = conexion.cursor()
        cursor.execute("SELECT activo FROM tareas WHERE id_tarea = ?", ("TAR-010",))
        fila = cursor.fetchone()
        assert fila is not None
        assert fila[0] == 1
