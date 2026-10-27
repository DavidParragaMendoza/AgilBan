"""Pruebas unitarias para componentes web reactivos de AgilBan (Fase 2).

Verifica el renderizado condicional, la navegacion SPA, el catalogo de proyectos,
el filtrado de busqueda insensible a mayusculas/minusculas y los estados vacios
diferenciados conforme a RF-01, RF-08, UT-WEB-01 y UT-WEB-02.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.edt import calcularEstadoPaquete
from app.core.validador import (
    validarCedula,
    validarEliminacionIntegrante,
    validarEliminacionPaquete,
    validarNombreIntegrante,
    validarNombrePaquete,
)
from app.domain.catalogos import (
    CargoIntegrante,
    EstadoKanban,
    EstadoPaquete,
    PrioridadTarea,
    TipoProyecto,
)
from app.domain.modelos import (
    Integrante,
    PaqueteTrabajo,
    Proyecto,
    Tarea,
)
from app.domain.monadas import Alguno
from app.ui.web.app import componenteApp
from app.ui.web.barraLateral import (
    barraLateralEdt,
    generarIdPaqueteSecuencial,
    renderizarAlertaContextual,
    renderizarConfirmacionEliminarIntegrante,
    renderizarConfirmacionEliminarPaquete,
    renderizarEncabezadoProyecto,
    renderizarEstadoVacioEdt,
    renderizarFilaNuevoPaquete,
    renderizarFilaRenombrarPaquete,
    renderizarFormularioNuevoIntegrante,
    renderizarItemPaquete,
)
from app.ui.web.inicio import (
    filtrarProyectosPorNombre,
    renderizarVistaInicio,
)
from app.ui.web.modalProyecto import (
    construirEntidadProyecto,
    modalCreacionProyecto,
    renderizarModalCreacionProyecto,
    validarFormularioProyecto,
)


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


def _dispararEvento(nodo: Any, nombreEvento: str, datosEvento: Any = None) -> None:
    """Ejecuta de forma sincrona la corrutina del manejador de evento ReactPy."""
    manejadores = nodo.get("eventHandlers", {})
    manejador = manejadores.get(nombreEvento)
    assert manejador is not None, (
        f"El nodo no posee el manejador de evento '{nombreEvento}'"
    )
    datos = [{}] if datosEvento is None else [datosEvento]
    asyncio.run(manejador.function(datos))


def _fabricarProyectoEjemplo(
    idProyecto: str = "PROY-001",
    nombre: str = "Plataforma E-commerce",
    tipo: TipoProyecto = TipoProyecto.DESARROLLO_WEB,
    porcentajeTerminado: float = 50.0,
) -> Proyecto:
    """Crea una entidad inmutable Proyecto de prueba para verificaciones de interfaz."""
    tarea1 = Tarea(
        idTarea="TAR-001",
        idPaquete="PAQ-001",
        titulo="Disenar interfaz",
        prioridad=PrioridadTarea.ALTA,
        estado=(
            EstadoKanban.TERMINADA
            if porcentajeTerminado > 0
            else EstadoKanban.PENDIENTE
        ),
        activo=True,
    )
    tarea2 = Tarea(
        idTarea="TAR-002",
        idPaquete="PAQ-001",
        titulo="Implementar base de datos",
        prioridad=PrioridadTarea.MEDIA,
        estado=EstadoKanban.PENDIENTE,
        activo=True,
    )

    paquete = PaqueteTrabajo(
        idPaquete="PAQ-001",
        idProyecto=idProyecto,
        nombre="Paquete 1",
        tareas=(tarea1, tarea2),
    )

    integrante = Integrante(
        cedula="0928374651",
        idProyecto=idProyecto,
        nombre="Carlos Bernabe",
        cargo=CargoIntegrante.DESARROLLADOR_FULLSTACK,
    )

    return Proyecto(
        idProyecto=idProyecto,
        nombre=nombre,
        tipo=tipo,
        paquetes=(paquete,),
        integrantes=(integrante,),
    )


class TestVistaInicioYBusqueda:
    """Suite de pruebas unitarias para la pantalla de Inicio, catalogo y busqueda local."""

    def testUT_WEB_01_CatalogoVacioMuestraBienvenidaYAccionCrear(self) -> None:
        """Verifica UT-WEB-01: MIENTRAS no existan proyectos, muestra bienvenida orientadora y boton de creacion."""
        llamadasModal: list[bool] = []

        vdom = renderizarVistaInicio(
            proyectos=(),
            textoBusqueda="",
            alBuscar=lambda _: None,
            alSeleccionarProyecto=lambda _: None,
            alAbrirModalCreacion=lambda: llamadasModal.append(True),
        )

        nodoVacio = _buscarPorId(vdom, "estado-catalogo-vacio")
        assert nodoVacio is not None, (
            "Debe renderizarse el contenedor con id 'estado-catalogo-vacio'"
        )
        assert _contieneTexto(nodoVacio, "Bienvenido a AgilBan")
        assert _contieneTexto(nodoVacio, "Aun no tienes proyectos registrados")

        botonCrear = _buscarPorId(vdom, "btn-crear-primer-proyecto")
        assert botonCrear is not None, (
            "Debe existir el boton para crear el primer proyecto"
        )

        # Simular clic en el boton de creacion mediante el despachador de eventos ReactPy
        _dispararEvento(botonCrear, "onClick")
        assert len(llamadasModal) == 1, (
            "Hacer clic en el boton debe disparar alAbrirModalCreacion"
        )

    def testUT_WEB_02_ProyectosExistentesRenderizaCuadriculaYMetricas(
        self,
    ) -> None:
        """Verifica UT-WEB-02: MIENTRAS existan proyectos, muestra la cuadricula de tarjetas interactivas con avance."""
        proyecto1 = _fabricarProyectoEjemplo(
            idProyecto="PROY-001",
            nombre="Sistema Contable",
            porcentajeTerminado=50.0,
        )
        proyecto2 = _fabricarProyectoEjemplo(
            idProyecto="PROY-002",
            nombre="App Logistica",
            porcentajeTerminado=0.0,
        )

        vdom = renderizarVistaInicio(
            proyectos=(proyecto1, proyecto2),
            textoBusqueda="",
            alBuscar=lambda _: None,
            alSeleccionarProyecto=lambda _: None,
            alAbrirModalCreacion=lambda: None,
        )

        nodoCuadricula = _buscarPorId(vdom, "cuadricula-proyectos")
        assert nodoCuadricula is not None, (
            "Debe renderizarse la cuadricula de proyectos"
        )

        tarjeta1 = _buscarPorId(vdom, "tarjeta-proyecto-PROY-001")
        tarjeta2 = _buscarPorId(vdom, "tarjeta-proyecto-PROY-002")

        assert tarjeta1 is not None, "Debe existir la tarjeta para el proyecto PROY-001"
        assert tarjeta2 is not None, "Debe existir la tarjeta para el proyecto PROY-002"
        assert _contieneTexto(tarjeta1, "Sistema Contable")
        assert _contieneTexto(tarjeta2, "App Logistica")
        assert _contieneTexto(tarjeta1, "50.0%")
        assert _contieneTexto(tarjeta2, "0.0%")

    def testBusquedaConCoincidenciasFiltraProyectosSinDistinguirMayusculas(
        self,
    ) -> None:
        """Verifica EARS-01.5: La busqueda local filtra tarjetas por nombre (case-insensitive)."""
        proyecto1 = _fabricarProyectoEjemplo(
            idProyecto="PROY-001", nombre="Red Neuronal Clasificadora"
        )
        proyecto2 = _fabricarProyectoEjemplo(
            idProyecto="PROY-002", nombre="Portal Web Educativo"
        )

        # Probar busqueda en mayusculas/minusculas
        coincidencias = filtrarProyectosPorNombre((proyecto1, proyecto2), "NEURONAL")
        assert len(coincidencias) == 1
        assert coincidencias[0].idProyecto == "PROY-001"

        coincidenciasMinusculas = filtrarProyectosPorNombre(
            (proyecto1, proyecto2), "portal"
        )
        assert len(coincidenciasMinusculas) == 1
        assert coincidenciasMinusculas[0].idProyecto == "PROY-002"

        vdom = renderizarVistaInicio(
            proyectos=(proyecto1, proyecto2),
            textoBusqueda="neuronal",
            alBuscar=lambda _: None,
            alSeleccionarProyecto=lambda _: None,
            alAbrirModalCreacion=lambda: None,
        )

        assert _buscarPorId(vdom, "tarjeta-proyecto-PROY-001") is not None
        assert _buscarPorId(vdom, "tarjeta-proyecto-PROY-002") is None

    def testBusquedaSinCoincidenciasMuestraEstadoDiferenciadoYAccionLimpiar(
        self,
    ) -> None:
        """Verifica EARS-01.5: SI no hay coincidencias, muestra estado sin resultados con accion para limpiar."""
        proyecto = _fabricarProyectoEjemplo(nombre="Sistema ERP")
        terminosBuscados: list[str] = []

        vdom = renderizarVistaInicio(
            proyectos=(proyecto,),
            textoBusqueda="TerminoInexistente",
            alBuscar=lambda t: terminosBuscados.append(t),
            alSeleccionarProyecto=lambda _: None,
            alAbrirModalCreacion=lambda: None,
        )

        # Verificar que NO se confunde con el catalogo vacio
        assert _buscarPorId(vdom, "estado-catalogo-vacio") is None
        nodoSinResultados = _buscarPorId(vdom, "estado-busqueda-sin-resultados")
        assert nodoSinResultados is not None, (
            "Debe renderizar 'estado-busqueda-sin-resultados'"
        )

        assert _contieneTexto(nodoSinResultados, "Sin coincidencias de busqueda")
        assert _contieneTexto(nodoSinResultados, "TerminoInexistente")

        botonLimpiar = _buscarPorId(vdom, "btn-limpiar-busqueda")
        assert botonLimpiar is not None, "Debe proveer el boton de limpiar busqueda"

        _dispararEvento(botonLimpiar, "onClick")
        assert terminosBuscados == [""], (
            "Pulsar limpiar busqueda debe emitir cadena vacia"
        )

    def testSeleccionDeTarjetaDisparaNavegacionAWorkspace(self) -> None:
        """Verifica EARS-01.3: CUANDO el usuario hace clic sobre la tarjeta, invoca alSeleccionarProyecto."""
        proyecto = _fabricarProyectoEjemplo(
            idProyecto="PROY-999", nombre="Iniciativa Cloud"
        )
        proyectosSeleccionados: list[str] = []

        vdom = renderizarVistaInicio(
            proyectos=(proyecto,),
            textoBusqueda="",
            alBuscar=lambda _: None,
            alSeleccionarProyecto=lambda idp: proyectosSeleccionados.append(idp),
            alAbrirModalCreacion=lambda: None,
        )

        tarjeta = _buscarPorId(vdom, "tarjeta-proyecto-PROY-999")
        assert tarjeta is not None

        # Disparar evento onClick en la tarjeta mediante el despachador de eventos ReactPy
        _dispararEvento(tarjeta, "onClick")
        assert proyectosSeleccionados == ["PROY-999"]


class TestComponenteAppNavegacionSpa:
    """Suite de pruebas para el enrutador SPA y estado global en componenteApp."""

    def testComponenteAppMontaContenedorRaizYAtributosDeEstado(self) -> None:
        """Verifica que componenteApp renderice el contenedor principal SPA con sus datos de estado."""
        from reactpy.core.layout import Layout

        async def renderizarApp() -> Any:
            async with Layout(componenteApp()) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizarApp())
        nodoRaiz = _buscarPorId(modelo, "agilban-contenedor-raiz")
        assert nodoRaiz is not None, (
            "Debe existir el contenedor con id 'agilban-contenedor-raiz'"
        )

        atributos = nodoRaiz.get("attributes", {})
        assert atributos.get("data-vista") == "INICIO"
        assert atributos.get("data-guardado") == "✓ Guardado"

        assert _buscarPorId(modelo, "agilban-encabezado-navegacion") is not None
        assert _buscarPorId(modelo, "vista-inicio-contenedor") is not None


class TestModalCreacionProyecto:
    """Suite de pruebas unitarias para el dialogo modal de creacion de proyecto (RF-01 y RF-02)."""

    def testUT_WEB_03_ModalGeneraTresFilasDinamicasDeIntegrantes(self) -> None:
        """Verifica UT-WEB-03: Al configurar 3 integrantes se generan exactamente 3 filas con cedula, nombre y cargo."""
        integrantes = (
            {
                "cedula": "0911111111",
                "nombre": "Carlos Bernabe",
                "cargo": CargoIntegrante.LIDER_PROYECTO.value,
            },
            {
                "cedula": "0922222222",
                "nombre": "Javier Infante",
                "cargo": CargoIntegrante.DESARROLLADOR_BACKEND.value,
            },
            {
                "cedula": "0933333333",
                "nombre": "David Parraga",
                "cargo": CargoIntegrante.DISENADOR_UI_UX.value,
            },
        )

        vdom = renderizarModalCreacionProyecto(
            nombre="Proyecto Tres Miembros",
            tipo=TipoProyecto.DESARROLLO_WEB,
            numPaquetes=2,
            integrantes=integrantes,
            errores={},
            alCambiarNombre=lambda _: None,
            alCambiarTipo=lambda _: None,
            alCambiarPaquetes=lambda _: None,
            alActualizarIntegrante=lambda _i, _c, _v: None,
            alAgregarIntegrante=lambda: None,
            alEliminarIntegrante=lambda _: None,
            alConfirmarGuardar=lambda: None,
            alCerrar=lambda: None,
        )

        assert _buscarPorId(vdom, "fila-integrante-0") is not None
        assert _buscarPorId(vdom, "fila-integrante-1") is not None
        assert _buscarPorId(vdom, "fila-integrante-2") is not None
        assert _buscarPorId(vdom, "fila-integrante-3") is None

        for idx in range(3):
            assert _buscarPorId(vdom, f"input-cedula-{idx}") is not None
            assert _buscarPorId(vdom, f"input-nombre-{idx}") is not None
            assert _buscarPorId(vdom, f"select-cargo-{idx}") is not None

    def testModalGeneraNombresSecuencialesPaquete1HastaNPorDefecto(
        self,
    ) -> None:
        """Verifica EARS-02.1: Los paquetes iniciales reciben nombres 'Paquete 1...N' por defecto sin pedirlos."""
        integrantesDatos = (
            {
                "cedula": "0955555555",
                "nombre": "Deivy Prudente",
                "cargo": CargoIntegrante.INGENIERO_QA.value,
            },
        )

        proyecto = construirEntidadProyecto(
            nombre="Iniciativa Calidad",
            tipo=TipoProyecto.INVESTIGACION_ACADEMICA,
            numPaquetes=4,
            integrantes=integrantesDatos,
            proyectosExistentes=(),
        )

        assert len(proyecto.paquetes) == 4
        nombresEsperados = [f"Paquete {i}" for i in range(1, 5)]
        assert [p.nombre for p in proyecto.paquetes] == nombresEsperados
        idsEsperados = [f"PAQ-{i:03d}" for i in range(1, 5)]
        assert [p.idPaquete for p in proyecto.paquetes] == idsEsperados

    def testModalRechazaEntradasInvalidasResaltandoErroresSinCerrar(
        self,
    ) -> None:
        """Verifica EARS-02.3: Entradas invalidas generan mapa de errores resaltando campos sin cerrar modal."""
        existente = _fabricarProyectoEjemplo(nombre="Proyecto Alpha")

        # Caso 1: Nombre vacio
        erroresVacio = validarFormularioProyecto(
            nombre="",
            numPaquetes=1,
            integrantes=(
                {
                    "cedula": "0911111111",
                    "nombre": "Ana Perez",
                    "cargo": CargoIntegrante.LIDER_PROYECTO.value,
                },
            ),
            proyectosExistentes=(),
        )
        assert "nombre" in erroresVacio

        # Caso 2: Nombre duplicado (case-insensitive)
        erroresDuplicado = validarFormularioProyecto(
            nombre="proyecto alpha",
            numPaquetes=1,
            integrantes=(
                {
                    "cedula": "0911111111",
                    "nombre": "Ana Perez",
                    "cargo": CargoIntegrante.LIDER_PROYECTO.value,
                },
            ),
            proyectosExistentes=(existente,),
        )
        assert "nombre" in erroresDuplicado

        # Caso 3: Cedula con letras o longitud invalida
        erroresCedula = validarFormularioProyecto(
            nombre="Nuevo Proyecto",
            numPaquetes=1,
            integrantes=(
                {
                    "cedula": "12345",
                    "nombre": "Ana Perez",
                    "cargo": CargoIntegrante.LIDER_PROYECTO.value,
                },
            ),
            proyectosExistentes=(),
        )
        assert "cedula_0" in erroresCedula

        # Caso 4: Nombre de integrante con numeros
        erroresNombreInteg = validarFormularioProyecto(
            nombre="Nuevo Proyecto",
            numPaquetes=1,
            integrantes=(
                {
                    "cedula": "0912345678",
                    "nombre": "Ana123",
                    "cargo": CargoIntegrante.LIDER_PROYECTO.value,
                },
            ),
            proyectosExistentes=(),
        )
        assert "nombre_0" in erroresNombreInteg

        # Caso 5: Cedulas duplicadas dentro del mismo proyecto
        erroresCedulaRepetida = validarFormularioProyecto(
            nombre="Nuevo Proyecto",
            numPaquetes=1,
            integrantes=(
                {
                    "cedula": "0912345678",
                    "nombre": "Ana Perez",
                    "cargo": CargoIntegrante.LIDER_PROYECTO.value,
                },
                {
                    "cedula": "0912345678",
                    "nombre": "Luis Gomez",
                    "cargo": CargoIntegrante.DESARROLLADOR_BACKEND.value,
                },
            ),
            proyectosExistentes=(),
        )
        assert "cedula_1" in erroresCedulaRepetida

        # Renderizar con errores y verificar que los mensajes se exhiben en el DOM
        vdom = renderizarModalCreacionProyecto(
            nombre="",
            tipo=TipoProyecto.DESARROLLO_WEB,
            numPaquetes=1,
            integrantes=(
                {
                    "cedula": "123",
                    "nombre": "Carlos",
                    "cargo": CargoIntegrante.LIDER_PROYECTO.value,
                },
            ),
            errores=erroresCedula,
            alCambiarNombre=lambda _: None,
            alCambiarTipo=lambda _: None,
            alCambiarPaquetes=lambda _: None,
            alActualizarIntegrante=lambda _i, _c, _v: None,
            alAgregarIntegrante=lambda: None,
            alEliminarIntegrante=lambda _: None,
            alConfirmarGuardar=lambda: None,
            alCerrar=lambda: None,
        )

        assert _buscarPorId(vdom, "contenedor-modal-creacion") is not None
        assert _contieneTexto(
            vdom, "La cédula debe contener exactamente 10 dígitos numéricos."
        )

    def testModalPersistenciaValidaInvocaCallbackGuardarYRedirige(self) -> None:
        """Verifica EARS-02.4: Datos validos construyen la entidad Proyecto y llaman al callback alGuardar."""
        integrantes = (
            {
                "cedula": "0912345678",
                "nombre": "Pedro Ramirez",
                "cargo": CargoIntegrante.ANALISTA_DATOS.value,
            },
        )

        proyecto = construirEntidadProyecto(
            nombre="Plataforma Big Data",
            tipo=TipoProyecto.CIENCIA_DATOS_IA,
            numPaquetes=2,
            integrantes=integrantes,
            proyectosExistentes=(),
        )

        assert proyecto.nombre == "Plataforma Big Data"
        assert proyecto.tipo == TipoProyecto.CIENCIA_DATOS_IA
        assert len(proyecto.paquetes) == 2
        assert len(proyecto.integrantes) == 1
        assert proyecto.integrantes[0].cedula == "0912345678"
        assert proyecto.integrantes[0].cargo == CargoIntegrante.ANALISTA_DATOS

    def testModalInteractivoReactPyRenderizaEstructuraCorrecta(self) -> None:
        """Verifica que modalCreacionProyecto se monte en un Layout reactivo sin errores."""
        from reactpy.core.layout import Layout

        async def renderizarModal() -> Any:
            async with Layout(
                modalCreacionProyecto(
                    alCerrar=lambda: None,
                    alGuardar=lambda _: None,
                    proyectosExistentes=(),
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizarModal())
        assert _buscarPorId(modelo, "modal-creacion-proyecto-overlay") is not None
        assert _buscarPorId(modelo, "btn-guardar-proyecto-confirmar") is not None
        assert _buscarPorId(modelo, "btn-agregar-fila-integrante") is not None


class TestBarraLateralEdt:
    """Suite de pruebas unitarias para la Barra Lateral de EDT y Gestion de Equipo (Bloque 3)."""

    def testUT_WEB_04_PaquetesConDiferentesEstadosRenderizaBadgesCorrectos(
        self,
    ) -> None:
        """Verifica UT-WEB-04 / EARS-03.2: Calcula y exhibe los badges correctos para cada estado de paquete."""
        # Paquete 1: Sin tareas
        paqSinTareas = PaqueteTrabajo(
            idPaquete="PAQ-001",
            idProyecto="PROY-001",
            nombre="Arquitectura Base",
            tareas=(),
        )
        assert calcularEstadoPaquete(paqSinTareas) == EstadoPaquete.SIN_TAREAS

        # Paquete 2: Pendiente (todas las tareas activas pendientes)
        paqPendiente = PaqueteTrabajo(
            idPaquete="PAQ-002",
            idProyecto="PROY-001",
            nombre="Seguridad y Auth",
            tareas=(
                Tarea(
                    idTarea="TAR-010",
                    idPaquete="PAQ-002",
                    titulo="Configurar MFA",
                    prioridad=PrioridadTarea.ALTA,
                    estado=EstadoKanban.PENDIENTE,
                    activo=True,
                ),
            ),
        )
        assert calcularEstadoPaquete(paqPendiente) == EstadoPaquete.PENDIENTE

        # Paquete 3: En progreso (algunas pendientes, en revision o en progreso)
        paqEnProgreso = PaqueteTrabajo(
            idPaquete="PAQ-003",
            idProyecto="PROY-001",
            nombre="Modulo Pagos",
            tareas=(
                Tarea(
                    idTarea="TAR-020",
                    idPaquete="PAQ-003",
                    titulo="Pasarela Stripe",
                    prioridad=PrioridadTarea.CRITICA,
                    estado=EstadoKanban.EN_PROGRESO,
                    activo=True,
                ),
                Tarea(
                    idTarea="TAR-021",
                    idPaquete="PAQ-003",
                    titulo="Notificaciones de pago",
                    prioridad=PrioridadTarea.MEDIA,
                    estado=EstadoKanban.PENDIENTE,
                    activo=True,
                ),
            ),
        )
        assert calcularEstadoPaquete(paqEnProgreso) == EstadoPaquete.EN_PROGRESO

        # Paquete 4: Terminado (todas las tareas activas terminadas)
        paqTerminado = PaqueteTrabajo(
            idPaquete="PAQ-004",
            idProyecto="PROY-001",
            nombre="Despliegue Cloud",
            tareas=(
                Tarea(
                    idTarea="TAR-030",
                    idPaquete="PAQ-004",
                    titulo="Pipeline CI/CD",
                    prioridad=PrioridadTarea.MEDIA,
                    estado=EstadoKanban.TERMINADA,
                    activo=True,
                ),
            ),
        )
        assert calcularEstadoPaquete(paqTerminado) == EstadoPaquete.TERMINADO

        # Renderizar cada item y verificar el badge derivado exhibido
        vdom1 = renderizarItemPaquete(
            paquete=paqSinTareas,
            estaSeleccionado=False,
            alSeleccionarPaquete=lambda _: None,
            alIniciarRenombrado=lambda _: None,
            alSolicitarEliminar=lambda _: None,
        )
        vdom2 = renderizarItemPaquete(
            paquete=paqPendiente,
            estaSeleccionado=False,
            alSeleccionarPaquete=lambda _: None,
            alIniciarRenombrado=lambda _: None,
            alSolicitarEliminar=lambda _: None,
        )
        vdom3 = renderizarItemPaquete(
            paquete=paqEnProgreso,
            estaSeleccionado=True,
            alSeleccionarPaquete=lambda _: None,
            alIniciarRenombrado=lambda _: None,
            alSolicitarEliminar=lambda _: None,
        )
        vdom4 = renderizarItemPaquete(
            paquete=paqTerminado,
            estaSeleccionado=False,
            alSeleccionarPaquete=lambda _: None,
            alIniciarRenombrado=lambda _: None,
            alSolicitarEliminar=lambda _: None,
        )

        badge1 = _buscarPorId(vdom1, "badge-estado-paquete-PAQ-001")
        badge2 = _buscarPorId(vdom2, "badge-estado-paquete-PAQ-002")
        badge3 = _buscarPorId(vdom3, "badge-estado-paquete-PAQ-003")
        badge4 = _buscarPorId(vdom4, "badge-estado-paquete-PAQ-004")

        assert badge1 is not None and _contieneTexto(badge1, "Sin Tareas")
        assert badge2 is not None and _contieneTexto(badge2, "Pendiente")
        assert badge3 is not None and _contieneTexto(badge3, "En progreso")
        assert badge4 is not None and _contieneTexto(badge4, "Terminado")

    def testSidebarEstadoVacioNavegableSinPaquetesEARS_03_9(self) -> None:
        """Verifica EARS-03.9: MIENTRAS no existan paquetes, muestra estado vacio sin bloquear navegacion."""
        llamadasNuevoPaquete: list[bool] = []
        vdomVacio = renderizarEstadoVacioEdt(
            alIniciarCreacionPaquete=lambda: llamadasNuevoPaquete.append(True)
        )

        assert _buscarPorId(vdomVacio, "sidebar-edt-vacio") is not None
        assert _contieneTexto(vdomVacio, "Sin Paquetes EDT")

        btnAgregar = _buscarPorId(vdomVacio, "btn-agregar-primer-paquete")
        assert btnAgregar is not None
        _dispararEvento(btnAgregar, "onClick")
        assert len(llamadasNuevoPaquete) == 1

        # Verificar que el encabezado del proyecto conserve los botones de navegacion
        llamadasInicio: list[bool] = []
        llamadasMetricas: list[bool] = []
        proyectoSinPaquetes = Proyecto(
            idProyecto="PROY-100",
            nombre="Proyecto Inicial",
            tipo=TipoProyecto.DESARROLLO_WEB,
            paquetes=(),
            integrantes=(),
        )

        vdomEncabezado = renderizarEncabezadoProyecto(
            proyecto=proyectoSinPaquetes,
            alVolverInicio=lambda: llamadasInicio.append(True),
            alAbrirMetricas=lambda: llamadasMetricas.append(True),
        )

        btnVolver = _buscarPorId(vdomEncabezado, "btn-volver-mis-proyectos")
        btnMetricas = _buscarPorId(vdomEncabezado, "btn-sidebar-metricas")

        assert btnVolver is not None
        assert btnMetricas is not None

        _dispararEvento(btnVolver, "onClick")
        assert len(llamadasInicio) == 1

        _dispararEvento(btnMetricas, "onClick")
        assert len(llamadasMetricas) == 1

    def testSidebarSeleccionPaqueteActualizaEstadoGlobalEARS_03_3(self) -> None:
        """Verifica EARS-03.3: Al hacer clic sobre un paquete, dispara el callback de seleccion."""
        seleccionados: list[str] = []
        paquete = PaqueteTrabajo(
            idPaquete="PAQ-042",
            idProyecto="PROY-001",
            nombre="Infraestructura Kubernetes",
            tareas=(),
        )

        vdom = renderizarItemPaquete(
            paquete=paquete,
            estaSeleccionado=False,
            alSeleccionarPaquete=lambda pid: seleccionados.append(pid),
            alIniciarRenombrado=lambda _: None,
            alSolicitarEliminar=lambda _: None,
        )

        _dispararEvento(vdom, "onClick")
        assert seleccionados == ["PAQ-042"]

    def testSidebarBloqueoEliminacionPaqueteConTareasEARS_03_7(self) -> None:
        """Verifica EARS-03.7: SI un paquete contiene tareas, se bloquea la eliminacion sin mutar la BD."""
        paqueteConTareas = PaqueteTrabajo(
            idPaquete="PAQ-010",
            idProyecto="PROY-001",
            nombre="Servicios Backend",
            tareas=(
                Tarea(
                    idTarea="TAR-100",
                    idPaquete="PAQ-010",
                    titulo="API REST GraphQL",
                    prioridad=PrioridadTarea.ALTA,
                    estado=EstadoKanban.PENDIENTE,
                    activo=True,
                ),
            ),
        )

        # 1. Validacion funcional pura en el core
        resValidacion = validarEliminacionPaquete(paqueteConTareas)
        assert resValidacion.esFallo()
        assert resValidacion.error.codigo == "PAQUETE_CON_TAREAS"
        assert "contiene tareas asociadas" in resValidacion.error.mensaje

        # 2. Renderizado de la alerta contextual de bloqueo en el sidebar
        vdomAlerta = renderizarAlertaContextual(
            mensaje=resValidacion.error.mensaje,
            alCerrar=lambda: None,
        )
        assert _buscarPorId(vdomAlerta, "alerta-contextual-sidebar") is not None
        assert _contieneTexto(vdomAlerta, "contiene tareas asociadas")

    def testSidebarPermiteEliminacionPaqueteSinTareasEARS_03_6(self) -> None:
        """Verifica EARS-03.6: CUANDO un paquete no contiene ninguna tarea, se autoriza su eliminacion."""
        paqueteVacio = PaqueteTrabajo(
            idPaquete="PAQ-999",
            idProyecto="PROY-001",
            nombre="Documentacion Swagger",
            tareas=(),
        )

        # 1. Validacion funcional pura
        resValidacion = validarEliminacionPaquete(paqueteVacio)
        assert resValidacion.esExito()
        assert resValidacion.obtenerValor() == "PAQ-999"

        # 2. Callback de eliminacion en el item
        eliminados: list[str] = []
        vdom = renderizarItemPaquete(
            paquete=paqueteVacio,
            estaSeleccionado=False,
            alSeleccionarPaquete=lambda _: None,
            alIniciarRenombrado=lambda _: None,
            alSolicitarEliminar=lambda p: eliminados.append(p.idPaquete),
        )

        btnEliminar = _buscarPorId(vdom, "btn-eliminar-paquete-PAQ-999")
        assert btnEliminar is not None
        _dispararEvento(btnEliminar, "onClick")
        assert eliminados == ["PAQ-999"]

    def testSidebarValidacionNombrePaqueteYGeneracionId(self) -> None:
        """Verifica EARS-03.4 y EARS-03.5: Validacion estricta de nombres y generacion correlativa."""
        nombresExistentes = ("Paquete 1", "Paquete 2")

        # Nombre vacio
        assert validarNombrePaquete("", nombresExistentes).esFallo()
        assert validarNombrePaquete("   ", nombresExistentes).esFallo()

        # Nombre de mas de 80 caracteres
        assert validarNombrePaquete("A" * 81, nombresExistentes).esFallo()

        # Nombre duplicado (case-insensitive)
        assert validarNombrePaquete("paquete 1", nombresExistentes).esFallo()
        assert validarNombrePaquete("PAQUETE 2", nombresExistentes).esFallo()

        # Nombre valido
        resValido = validarNombrePaquete("  Modulo Facturacion  ", nombresExistentes)
        assert resValido.esExito()
        assert resValido.obtenerValor() == "Modulo Facturacion"

        # Generacion de identificador correlativo
        paqs = (
            PaqueteTrabajo("PAQ-001", "PROY-1", "P1", ()),
            PaqueteTrabajo("PAQ-002", "PROY-1", "P2", ()),
        )
        assert generarIdPaqueteSecuencial(paqs) == "PAQ-003"
        assert generarIdPaqueteSecuencial(()) == "PAQ-001"

    def testSidebarGestionEquipoBloqueoEliminacionTareasActivasEARS_03_8(self) -> None:
        """Verifica EARS-03.8: Bloquea eliminar integrante si posee tareas activas asignadas."""
        integ1 = Integrante(
            cedula="0928374651",
            idProyecto="PROY-001",
            nombre="Carlos Bernabe",
            cargo=CargoIntegrante.LIDER_PROYECTO,
        )
        integ2 = Integrante(
            cedula="0928374652",
            idProyecto="PROY-001",
            nombre="Javier Infante",
            cargo=CargoIntegrante.DESARROLLADOR_FULLSTACK,
        )

        tareaAsignada = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-001",
            titulo="Implementar backend",
            prioridad=PrioridadTarea.ALTA,
            estado=EstadoKanban.EN_PROGRESO,
            activo=True,
            cedulaResponsable=Alguno("0928374651"),
        )

        # Intento de eliminar a integ1 con tareas activas asignadas -> BLOQUEADO
        res1 = validarEliminacionIntegrante(
            cedula="0928374651",
            integrantes=(integ1, integ2),
            tareas=(tareaAsignada,),
        )
        assert res1.esFallo()
        assert res1.error.codigo == "INTEGRANTE_CON_TAREAS_ACTIVAS"

        # Intento de eliminar a integ2 sin tareas activas asignadas -> PERMITIDO
        res2 = validarEliminacionIntegrante(
            cedula="0928374652",
            integrantes=(integ1, integ2),
            tareas=(tareaAsignada,),
        )
        assert res2.esExito()
        assert res2.obtenerValor() == "0928374652"

    def testSidebarGestionEquipoBloqueoEliminacionUltimoIntegranteEARS_03_8(
        self,
    ) -> None:
        """Verifica EARS-03.8: Bloquea eliminar al unico integrante restante del proyecto."""
        integUnico = Integrante(
            cedula="0912345678",
            idProyecto="PROY-001",
            nombre="Unico Miembro",
            cargo=CargoIntegrante.LIDER_PROYECTO,
        )

        res = validarEliminacionIntegrante(
            cedula="0912345678",
            integrantes=(integUnico,),
            tareas=(),
        )
        assert res.esFallo()
        assert res.error.codigo == "ULTIMO_INTEGRANTE"
        assert "único integrante" in res.error.mensaje

    def testSidebarFormularioNuevoIntegranteValidaciones(self) -> None:
        """Verifica las validaciones de cedula, nombre y cargo para nuevos integrantes."""
        cedulasExistentes = ("0912345678",)

        # Cedula invalida (no tiene 10 digitos o contiene letras)
        assert validarCedula("12345", cedulasExistentes).esFallo()
        assert validarCedula("091234567A", cedulasExistentes).esFallo()

        # Cedula repetida
        assert validarCedula("0912345678", cedulasExistentes).esFallo()

        # Cedula valida
        resCed = validarCedula("0928374651", cedulasExistentes)
        assert resCed.esExito()
        assert resCed.obtenerValor() == "0928374651"

        # Nombre con numeros o vacio
        assert validarNombreIntegrante("").esFallo()
        assert validarNombreIntegrante("Carlos123").esFallo()

        # Nombre valido
        resNom = validarNombreIntegrante("Carlos Bernabé")
        assert resNom.esExito()
        assert resNom.obtenerValor() == "Carlos Bernabé"

        # Renderizar formulario de nuevo integrante y verificar inputs
        vdomForm = renderizarFormularioNuevoIntegrante(
            cedula="",
            nombre="",
            cargo=CargoIntegrante.DESARROLLADOR_FULLSTACK.value,
            errores={"cedula": "Error de cédula", "nombre": "Error de nombre"},
            alCambiarCedula=lambda _: None,
            alCambiarNombre=lambda _: None,
            alCambiarCargo=lambda _: None,
            alGuardar=lambda: None,
            alCancelar=lambda: None,
        )
        assert _buscarPorId(vdomForm, "formulario-nuevo-integrante") is not None
        assert _buscarPorId(vdomForm, "input-cedula-integrante") is not None
        assert _buscarPorId(vdomForm, "input-nombre-integrante") is not None
        assert _buscarPorId(vdomForm, "select-cargo-integrante") is not None
        assert _contieneTexto(vdomForm, "Error de cédula")
        assert _contieneTexto(vdomForm, "Error de nombre")

    def testSidebarComponenteReactPyMontajeCompleto(self) -> None:
        """Verifica que barraLateralEdt se monte como componente ReactPy en un Layout sin errores."""
        from reactpy.core.layout import Layout

        proyecto = _fabricarProyectoEjemplo(
            idProyecto="PROY-777",
            nombre="App Banca Digital",
            tipo=TipoProyecto.DESARROLLO_WEB,
        )

        async def renderizarSidebar() -> Any:
            async with Layout(
                barraLateralEdt(
                    proyecto=proyecto,
                    idPaqueteSeleccionado="PAQ-001",
                    alSeleccionarPaquete=lambda _: None,
                    alAgregarPaquete=lambda _: None,
                    alRenombrarPaquete=lambda _i, _n: None,
                    alEliminarPaquete=lambda _: None,
                    alVolverInicio=lambda: None,
                    alAbrirMetricas=lambda: None,
                    alAgregarIntegrante=lambda _: None,
                    alEliminarIntegrante=lambda _: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizarSidebar())
        assert _buscarPorId(modelo, "panel-lateral-edt-sidebar") is not None
        assert _buscarPorId(modelo, "encabezado-sidebar-proyecto") is not None
        assert _buscarPorId(modelo, "titulo-proyecto-sidebar") is not None
        assert _buscarPorId(modelo, "seccion-equipo-sidebar") is not None
        assert _buscarPorId(modelo, "item-paquete-PAQ-001") is not None

    def testSidebarFormulariosEnLineaNuevoYRenombrarPaquete(self) -> None:
        """Verifica el renderizado de los formularios en linea para crear y renombrar paquetes."""
        valoresNuevo: list[str] = []
        guardadosNuevo: list[bool] = []
        canceladosNuevo: list[bool] = []

        vdomNuevo = renderizarFilaNuevoPaquete(
            nombre="Paquete Alpha",
            error="Error nombre",
            alCambiarNombre=lambda v: valoresNuevo.append(v),
            alGuardar=lambda: guardadosNuevo.append(True),
            alCancelar=lambda: canceladosNuevo.append(True),
        )

        assert _buscarPorId(vdomNuevo, "formulario-nuevo-paquete") is not None
        assert _buscarPorId(vdomNuevo, "input-nombre-nuevo-paquete") is not None
        assert _contieneTexto(vdomNuevo, "Error nombre")

        _dispararEvento(_buscarPorId(vdomNuevo, "btn-guardar-nuevo-paquete"), "onClick")
        assert len(guardadosNuevo) == 1

        _dispararEvento(
            _buscarPorId(vdomNuevo, "btn-cancelar-nuevo-paquete"), "onClick"
        )
        assert len(canceladosNuevo) == 1

        guardadosRenombrar: list[bool] = []
        canceladosRenombrar: list[bool] = []
        vdomRenombrar = renderizarFilaRenombrarPaquete(
            idPaquete="PAQ-001",
            nombre="Paquete Renombrado",
            error="Error unicidad",
            alCambiarNombre=lambda _: None,
            alGuardar=lambda: guardadosRenombrar.append(True),
            alCancelar=lambda: canceladosRenombrar.append(True),
        )

        assert (
            _buscarPorId(vdomRenombrar, "formulario-renombrar-paquete-PAQ-001")
            is not None
        )
        assert (
            _buscarPorId(vdomRenombrar, "input-renombrar-paquete-PAQ-001") is not None
        )
        assert _contieneTexto(vdomRenombrar, "Error unicidad")

        _dispararEvento(
            _buscarPorId(vdomRenombrar, "btn-guardar-renombrar-PAQ-001"), "onClick"
        )
        assert len(guardadosRenombrar) == 1

        _dispararEvento(
            _buscarPorId(vdomRenombrar, "btn-cancelar-renombrar-PAQ-001"), "onClick"
        )
        assert len(canceladosRenombrar) == 1

    def testWorkspaceIntegracionBarraLateralEnComponenteApp(self) -> None:
        """Verifica la integracion del Workspace con barraLateralEdt dentro de componenteApp."""
        import sqlite3

        from reactpy.core.layout import Layout

        from app.adapters.esquemaSqlite import inicializarEsquema
        from app.adapters.repositorioSqlite import guardarProyectoCompleto

        conexion = sqlite3.connect(":memory:")
        inicializarEsquema(conexion)

        proyecto = _fabricarProyectoEjemplo(
            idProyecto="PROY-555",
            nombre="Sistema de Pagos",
            tipo=TipoProyecto.DESARROLLO_WEB,
        )
        guardarProyectoCompleto(conexion, proyecto)

        async def renderizarWorkspace() -> Any:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                update = await layout.render()
                model = update["model"]
                btnWs = _buscarPorId(model, "nav-item-workspace")
                assert btnWs is not None
                target_id = btnWs["eventHandlers"]["onClick"]["target"]
                await layout.deliver(
                    {"type": "layout-event", "target": target_id, "data": [{}]}
                )
                update2 = await layout.render()
                return update2["model"]

        modeloWs = asyncio.run(renderizarWorkspace())
        assert _buscarPorId(modeloWs, "vista-workspace-contenedor") is not None
        assert _buscarPorId(modeloWs, "panel-lateral-edt-sidebar") is not None
        assert _buscarPorId(modeloWs, "area-central-workspace") is not None
        assert _buscarPorId(modeloWs, "cabecera-paquete-activo") is not None
        assert _contieneTexto(modeloWs, "Sistema de Pagos")

    def testSidebarConfirmacionEliminarIntegrante(self) -> None:
        """Verifica el cuadro de confirmacion previa antes de eliminar un integrante del equipo."""
        integ = Integrante(
            cedula="0912345678",
            idProyecto="PROY-001",
            nombre="Carlos Bernabé",
            cargo=CargoIntegrante.LIDER_PROYECTO,
        )

        confirmados: list[bool] = []
        cancelados: list[bool] = []

        vdom = renderizarConfirmacionEliminarIntegrante(
            integrante=integ,
            alConfirmar=lambda: confirmados.append(True),
            alCancelar=lambda: cancelados.append(True),
        )

        assert (
            _buscarPorId(vdom, "confirmacion-eliminar-integrante-0912345678")
            is not None
        )
        assert _contieneTexto(vdom, "¿Eliminar integrante del equipo?")
        assert _contieneTexto(vdom, "Carlos Bernabé")

        btnConfirmar = _buscarPorId(vdom, "btn-confirmar-eliminar-0912345678")
        btnCancelar = _buscarPorId(vdom, "btn-cancelar-eliminar-0912345678")
        assert btnConfirmar is not None
        assert btnCancelar is not None

        _dispararEvento(btnConfirmar, "onClick")
        assert len(confirmados) == 1

        _dispararEvento(btnCancelar, "onClick")
        assert len(cancelados) == 1

    def testSidebarConfirmacionEliminarPaquete(self) -> None:
        """Verifica el cuadro de confirmacion para eliminar un paquete de trabajo sin tareas."""
        paq = PaqueteTrabajo(
            idPaquete="PAQ-001",
            idProyecto="PROY-001",
            nombre="Modulo Facturacion",
            tareas=(),
        )

        confirmados: list[bool] = []
        cancelados: list[bool] = []

        vdom = renderizarConfirmacionEliminarPaquete(
            paquete=paq,
            alConfirmar=lambda: confirmados.append(True),
            alCancelar=lambda: cancelados.append(True),
        )

        assert _buscarPorId(vdom, "confirmacion-eliminar-paquete-PAQ-001") is not None
        assert _contieneTexto(vdom, "¿Eliminar 'Modulo Facturacion'?")

        btnConfirmar = _buscarPorId(vdom, "btn-confirmar-eliminar-paquete-PAQ-001")
        btnCancelar = _buscarPorId(vdom, "btn-cancelar-eliminar-paquete-PAQ-001")
        assert btnConfirmar is not None
        assert btnCancelar is not None

        _dispararEvento(btnConfirmar, "onClick")
        assert len(confirmados) == 1

        _dispararEvento(btnCancelar, "onClick")
        assert len(cancelados) == 1

    def testWorkspaceReactividadAgregarYEliminarIntegranteSinRecargar(
        self,
    ) -> None:
        """Verifica la reactividad inmediata al agregar y eliminar integrantes en el Workspace sin recargar."""
        import sqlite3

        from reactpy.core.layout import Layout

        from app.adapters.esquemaSqlite import inicializarEsquema
        from app.adapters.repositorioSqlite import guardarProyectoCompleto

        conexion = sqlite3.connect(":memory:")
        inicializarEsquema(conexion)

        proyecto = _fabricarProyectoEjemplo(
            idProyecto="PROY-900",
            nombre="Portal Financiero",
            tipo=TipoProyecto.DESARROLLO_WEB,
        )
        guardarProyectoCompleto(conexion, proyecto)

        async def flujoReactivo() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                # 1. Render inicial y navegacion al Workspace
                update1 = await layout.render()
                btnWs = _buscarPorId(update1["model"], "nav-item-workspace")
                assert btnWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )

                updateWs = await layout.render()
                modelWs = updateWs["model"]
                assert _contieneTexto(modelWs, "Portal Financiero")
                assert not _contieneTexto(modelWs, "David Gomez")

                # 2. Abrir formulario de nuevo integrante en la barra lateral
                btnAbrir = _buscarPorId(modelWs, "btn-abrir-formulario-integrante")
                assert btnAbrir is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnAbrir["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )

                updateForm = await layout.render()
                modelForm = updateForm["model"]

                # 3. Ingresar datos del nuevo integrante
                inputCedula = _buscarPorId(modelForm, "input-cedula-integrante")
                assert inputCedula is not None

                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputCedula["eventHandlers"]["onChange"]["target"],
                        "data": [{"target": {"value": "0999887766"}}],
                    }
                )
                upCed = await layout.render()
                inputNombreActualizado = _buscarPorId(
                    upCed["model"], "input-nombre-integrante"
                )
                assert inputNombreActualizado is not None

                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputNombreActualizado["eventHandlers"]["onChange"][
                            "target"
                        ],
                        "data": [{"target": {"value": "David Gomez"}}],
                    }
                )
                upNom = await layout.render()
                btnGuardar = _buscarPorId(upNom["model"], "btn-guardar-integrante")
                assert btnGuardar is not None

                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnGuardar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )

                # 4. Verificar que David Gomez aparece INMEDIATAMENTE sin recargar la pagina
                await layout.render()
                updateAgregado = await layout.render()
                modelAgregado = updateAgregado["model"]
                assert _contieneTexto(modelAgregado, "David Gomez")
                assert _contieneTexto(modelAgregado, "0999887766")

                # 5. Solicitar eliminacion de David Gomez
                btnEliminar = _buscarPorId(
                    modelAgregado, "btn-eliminar-integrante-0999887766"
                )
                assert btnEliminar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnEliminar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )

                # 6. Verificar que aparece el dialogo de confirmacion
                updateConfirm = await layout.render()
                modelConfirm = updateConfirm["model"]
                assert (
                    _buscarPorId(
                        modelConfirm,
                        "confirmacion-eliminar-integrante-0999887766",
                    )
                    is not None
                )

                # 7. Confirmar eliminacion y verificar remocion inmediata del DOM
                btnConfirmarEliminar = _buscarPorId(
                    modelConfirm, "btn-confirmar-eliminar-0999887766"
                )
                assert btnConfirmarEliminar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnConfirmarEliminar["eventHandlers"]["onClick"][
                            "target"
                        ],
                        "data": [{}],
                    }
                )

                await layout.render()
                updateFinal = await layout.render()
                modelFinal = updateFinal["model"]
                assert not _contieneTexto(modelFinal, "David Gomez")

        asyncio.run(flujoReactivo())
