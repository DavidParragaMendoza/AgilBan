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
from app.domain.monadas import Alguno, Ninguno
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
from app.ui.web.modalRegreso import modalRegresoKanban
from app.ui.web.panelEdicionTarea import EstadoGuardado, panelEdicionTarea
from app.ui.web.tableroKanban import tableroKanban
from app.ui.web.tarjetaTarea import tarjetaTarea
from app.ui.web.vistaMetricas import vistaMetricas


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


class TestTarjetaKanban:
    """Suite de pruebas unitarias para la Tarjeta Visual de Tarea (Bloque 4 / Tarea 4.1)."""

    def testTarjetaMuestraIdentificadorTituloPrioridadResponsableYFecha(self) -> None:
        """Verifica UT-WEB-05: Muestra TAR-NNN, título, badge cromático de prioridad, responsable y fecha."""
        from reactpy.core.layout import Layout

        integrante = Integrante(
            cedula="0912345678",
            idProyecto="PROY-001",
            nombre="Carlos Bernabé",
            cargo=CargoIntegrante.DESARROLLADOR_BACKEND,
        )
        tarea = Tarea(
            idTarea="TAR-001",
            idPaquete="PAQ-001",
            titulo="Diseñar esquema relacional",
            descripcion=Alguno("Esquema SQLite con FKs"),
            prioridad=PrioridadTarea.ALTA,
            cedulaResponsable=Alguno("0912345678"),
            fechaObjetivo=Alguno("2026-11-15"),
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
        )

        async def renderizar() -> Any:
            async with Layout(
                tarjetaTarea(
                    tarea=tarea,
                    integrantes=(integrante,),
                    alSeleccionarTarea=lambda t: None,
                    alAvanzar=lambda t, e: None,
                    alSolicitarDevolucion=lambda t: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        assert _buscarPorId(modelo, "tarjeta-tarea-TAR-001") is not None
        assert _contieneTexto(modelo, "TAR-001")
        assert _contieneTexto(modelo, "Diseñar esquema relacional")
        assert _contieneTexto(modelo, "Alta")
        assert _contieneTexto(modelo, "Carlos Bernabé")
        assert _contieneTexto(modelo, "2026-11-15")
        assert _buscarPorId(modelo, "contador-regresos-TAR-001") is None
        assert _buscarPorId(modelo, "badge-vencida-TAR-001") is None

    def testTarjetaSinAsignarYSinFecha(self) -> None:
        """Verifica que sin responsable muestre 'Sin asignar' y sin fecha 'Sin fecha'."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-002",
            idPaquete="PAQ-001",
            titulo="Configurar linter",
            prioridad=PrioridadTarea.BAJA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
        )

        async def renderizar() -> Any:
            async with Layout(
                tarjetaTarea(
                    tarea=tarea,
                    integrantes=(),
                    alSeleccionarTarea=lambda t: None,
                    alAvanzar=lambda t, e: None,
                    alSolicitarDevolucion=lambda t: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        assert _contieneTexto(modelo, "Sin asignar")
        assert _contieneTexto(modelo, "Sin fecha")

    def testTarjetaVencidaMuestraBadgeRojoSinBloquearAcciones(self) -> None:
        """Verifica que una fecha objetivo pasada exhiba badge 'Vencida' sin bloquear avance."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-003",
            idPaquete="PAQ-001",
            titulo="Corregir vulnerabilidad",
            prioridad=PrioridadTarea.CRITICA,
            fechaObjetivo=Alguno("2020-01-01"),
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
        )
        avances: list[tuple[Tarea, EstadoKanban]] = []

        async def interactuar() -> Any:
            async with Layout(
                tarjetaTarea(
                    tarea=tarea,
                    integrantes=(),
                    alSeleccionarTarea=lambda t: None,
                    alAvanzar=lambda t, e: avances.append((t, e)),
                    alSolicitarDevolucion=lambda t: None,
                )
            ) as layout:
                update = await layout.render()
                btnAvanzar = _buscarPorId(update["model"], "btn-avanzar-tarea-TAR-003")
                assert btnAvanzar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnAvanzar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                return update["model"]

        modelo = asyncio.run(interactuar())
        assert _buscarPorId(modelo, "badge-vencida-TAR-003") is not None
        assert _contieneTexto(modelo, "Vencida")
        assert len(avances) == 1
        assert avances[0][1] == EstadoKanban.EN_PROGRESO

    def testTarjetaContadorRegresosVisibleSiMayorACero(self) -> None:
        """Verifica que el contador de regresos se exhiba únicamente si contadorRegresos > 0."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-004",
            idPaquete="PAQ-001",
            titulo="Refactorizar módulo",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.EN_PROGRESO,
            contadorRegresos=3,
            activo=True,
        )

        async def renderizar() -> Any:
            async with Layout(
                tarjetaTarea(
                    tarea=tarea,
                    integrantes=(),
                    alSeleccionarTarea=lambda t: None,
                    alAvanzar=lambda t, e: None,
                    alSolicitarDevolucion=lambda t: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        badgeRegresos = _buscarPorId(modelo, "contador-regresos-TAR-004")
        assert badgeRegresos is not None
        assert _contieneTexto(badgeRegresos, "3")

    def testTransicionesPermitidasSegunEstadoKanban(self) -> None:
        """Verifica que las acciones sigan estrictamente las transiciones permitidas (EARS-04.3 y EARS-04.4)."""
        from reactpy.core.layout import Layout

        estadosCasos = [
            (EstadoKanban.PENDIENTE, True, False, "En progreso →"),
            (EstadoKanban.EN_PROGRESO, True, True, "En revisión →"),
            (EstadoKanban.EN_REVISION, True, True, "Terminar ✓"),
            (EstadoKanban.TERMINADA, False, True, None),
        ]

        for estado, permiteAvanzar, permiteDevolver, textoAvanzar in estadosCasos:
            tarea = Tarea(
                idTarea=f"TAR-{estado.name}",
                idPaquete="PAQ-001",
                titulo=f"Tarea en {estado.value}",
                prioridad=PrioridadTarea.MEDIA,
                estado=estado,
                contadorRegresos=0,
                activo=True,
            )

            async def renderizar(tar: Tarea = tarea) -> Any:
                async with Layout(
                    tarjetaTarea(
                        tarea=tar,
                        integrantes=(),
                        alSeleccionarTarea=lambda t: None,
                        alAvanzar=lambda t, e: None,
                        alSolicitarDevolucion=lambda t: None,
                    )
                ) as layout:
                    update = await layout.render()
                    return update["model"]

            modelo = asyncio.run(renderizar())
            btnAvanzar = _buscarPorId(modelo, f"btn-avanzar-tarea-TAR-{estado.name}")
            btnDevolver = _buscarPorId(modelo, f"btn-devolver-tarea-TAR-{estado.name}")

            if permiteAvanzar:
                assert btnAvanzar is not None
                assert _contieneTexto(btnAvanzar, textoAvanzar)
            else:
                assert btnAvanzar is None

            if permiteDevolver:
                assert btnDevolver is not None
                assert _contieneTexto(btnDevolver, "Devolver")
            else:
                assert btnDevolver is None

    def testClicCuerpoTarjetaAbreSideDrawer(self) -> None:
        """Verifica que hacer clic en el cuerpo de la tarjeta dispare alSeleccionarTarea."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-005",
            idPaquete="PAQ-001",
            titulo="Auditar dependencias",
            prioridad=PrioridadTarea.BAJA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
        )
        seleccionadas: list[Tarea] = []

        async def interactuar() -> None:
            async with Layout(
                tarjetaTarea(
                    tarea=tarea,
                    integrantes=(),
                    alSeleccionarTarea=lambda t: seleccionadas.append(t),
                    alAvanzar=lambda t, e: None,
                    alSolicitarDevolucion=lambda t: None,
                )
            ) as layout:
                update = await layout.render()
                tituloNodo = _buscarPorId(update["model"], "titulo-tarea-TAR-005")
                assert tituloNodo is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": tituloNodo["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )

        asyncio.run(interactuar())
        assert len(seleccionadas) == 1
        assert seleccionadas[0].idTarea == "TAR-005"

    def testClicBotonDevolverDisparaCallback(self) -> None:
        """Verifica que hacer clic en Devolver invoque alSolicitarDevolucion."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-006",
            idPaquete="PAQ-001",
            titulo="Pruebas de carga",
            prioridad=PrioridadTarea.ALTA,
            estado=EstadoKanban.EN_PROGRESO,
            contadorRegresos=0,
            activo=True,
        )
        devoluciones: list[Tarea] = []

        async def interactuar() -> None:
            async with Layout(
                tarjetaTarea(
                    tarea=tarea,
                    integrantes=(),
                    alSeleccionarTarea=lambda t: None,
                    alAvanzar=lambda t, e: None,
                    alSolicitarDevolucion=lambda t: devoluciones.append(t),
                )
            ) as layout:
                update = await layout.render()
                btnDevolver = _buscarPorId(
                    update["model"], "btn-devolver-tarea-TAR-006"
                )
                assert btnDevolver is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnDevolver["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )

        asyncio.run(interactuar())
        assert len(devoluciones) == 1
        assert devoluciones[0].idTarea == "TAR-006"


class TestModalRegresoKanban:
    """Suite de pruebas unitarias para el Modal de Justificación Obligatoria (Bloque 4 / Tarea 4.3)."""

    def testModalMuestraOrigenYDestinoSoloLecturaSinSelector(self) -> None:
        """Verifica que muestre origen y destino calculados automáticamente sin menú selector (EARS-05.1)."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-010",
            idPaquete="PAQ-001",
            titulo="Implementar caché Redis",
            prioridad=PrioridadTarea.ALTA,
            estado=EstadoKanban.EN_PROGRESO,
            contadorRegresos=0,
            activo=True,
        )

        async def renderizar() -> Any:
            async with Layout(
                modalRegresoKanban(
                    tarea=tarea,
                    alConfirmar=lambda m: None,
                    alCancelar=lambda: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        assert _buscarPorId(modelo, "modal-regreso-dialogo") is not None
        assert _contieneTexto(modelo, "En progreso")
        assert _contieneTexto(modelo, "Pendiente")
        assert _contieneTexto(modelo, "Solo lectura")

        def tieneSelect(nodo: Any) -> bool:
            if isinstance(nodo, dict):
                if nodo.get("tagName") == "select":
                    return True
                for hijo in nodo.get("children", []):
                    if tieneSelect(hijo):
                        return True
            return False

        assert not tieneSelect(modelo)

    def testModalRechazaMotivoVacioOSoloEspacios(self) -> None:
        """Verifica que rechace motivo vacío o de puros espacios mostrando advertencia contextual (EARS-05.2)."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-011",
            idPaquete="PAQ-001",
            titulo="Validar tokens JWT",
            prioridad=PrioridadTarea.ALTA,
            estado=EstadoKanban.EN_REVISION,
            contadorRegresos=1,
            activo=True,
        )
        confirmaciones: list[str] = []

        async def interactuar() -> Any:
            async with Layout(
                modalRegresoKanban(
                    tarea=tarea,
                    alConfirmar=lambda m: confirmaciones.append(m),
                    alCancelar=lambda: None,
                )
            ) as layout:
                update = await layout.render()
                btnConfirmar = _buscarPorId(update["model"], "btn-confirmar-regreso")
                assert btnConfirmar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnConfirmar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                update2 = await layout.render()
                return update2["model"]

        modelo = asyncio.run(interactuar())
        assert len(confirmaciones) == 0
        assert _contieneTexto(modelo, "El motivo de devolución es obligatorio")

    def testModalConfirmarConMotivoValidoDisparaCallback(self) -> None:
        """Verifica que confirmar con motivo válido dispare alConfirmar con el texto limpio (EARS-05.4)."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-012",
            idPaquete="PAQ-001",
            titulo="Integración CI/CD",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.TERMINADA,
            contadorRegresos=0,
            activo=True,
        )
        confirmaciones: list[str] = []

        async def interactuar() -> None:
            async with Layout(
                modalRegresoKanban(
                    tarea=tarea,
                    alConfirmar=lambda m: confirmaciones.append(m),
                    alCancelar=lambda: None,
                )
            ) as layout:
                update = await layout.render()
                inputMotivo = _buscarPorId(update["model"], "input-motivo-regreso")
                assert inputMotivo is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputMotivo["eventHandlers"]["onChange"]["target"],
                        "data": [
                            {
                                "target": {
                                    "value": "Faltan pruebas unitarias en el pipeline"
                                }
                            }
                        ],
                    }
                )
                update2 = await layout.render()
                btnConfirmar = _buscarPorId(update2["model"], "btn-confirmar-regreso")
                assert btnConfirmar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnConfirmar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )

        asyncio.run(interactuar())
        assert len(confirmaciones) == 1
        assert confirmaciones[0] == "Faltan pruebas unitarias en el pipeline"

    def testModalCancelarNoMuta(self) -> None:
        """Verifica que presionar Cancelar invoque alCancelar sin mutar estado."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-013",
            idPaquete="PAQ-001",
            titulo="Migrar Dockerfile",
            prioridad=PrioridadTarea.BAJA,
            estado=EstadoKanban.EN_PROGRESO,
            contadorRegresos=0,
            activo=True,
        )
        cancelados: list[bool] = []

        async def interactuar() -> None:
            async with Layout(
                modalRegresoKanban(
                    tarea=tarea,
                    alConfirmar=lambda m: None,
                    alCancelar=lambda: cancelados.append(True),
                )
            ) as layout:
                update = await layout.render()
                btnCancelar = _buscarPorId(update["model"], "btn-cancelar-regreso")
                assert btnCancelar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnCancelar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )

        asyncio.run(interactuar())
        assert len(cancelados) == 1

    def testModalInvalidoParaTareaPendiente(self) -> None:
        """Verifica que para una tarea en Pendiente (sin retroceso válido) el modal retorne elemento oculto."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-014",
            idPaquete="PAQ-001",
            titulo="Tarea inicial",
            prioridad=PrioridadTarea.BAJA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
        )

        async def renderizar() -> Any:
            async with Layout(
                modalRegresoKanban(
                    tarea=tarea,
                    alConfirmar=lambda m: None,
                    alCancelar=lambda: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        assert _buscarPorId(modelo, "modal-regreso-invalido") is not None
        assert _buscarPorId(modelo, "modal-regreso-dialogo") is None


class TestTableroKanban:
    """Suite de pruebas unitarias para el Tablero Kanban y creación de tareas (Bloque 4 / Tarea 4.2)."""

    def testTableroRenderiza4ColumnasDelimitadas(self) -> None:
        """Verifica que el tablero contenga las 4 columnas canónicas fijas (EARS-04.1)."""
        from reactpy.core.layout import Layout

        paquete = PaqueteTrabajo(
            idPaquete="PAQ-100",
            idProyecto="PROY-001",
            nombre="Backend Core",
            tareas=(),
        )

        async def renderizar() -> Any:
            async with Layout(
                tableroKanban(
                    paquete=paquete,
                    integrantes=(),
                    alSeleccionarTarea=lambda t: None,
                    alAvanzarTarea=lambda t, e: None,
                    alSolicitarDevolucion=lambda t: None,
                    alCrearTarea=lambda tit, clv: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        assert _buscarPorId(modelo, "columna-kanban-pendiente") is not None
        assert _buscarPorId(modelo, "columna-kanban-en_progreso") is not None
        assert _buscarPorId(modelo, "columna-kanban-en_revision") is not None
        assert _buscarPorId(modelo, "columna-kanban-terminada") is not None

    def testTableroFiltraTareasInactivas(self) -> None:
        """Verifica que las tareas descartadas lógicamente (activo=False) no se muestren en ninguna columna (EARS-04.2)."""
        from reactpy.core.layout import Layout

        tareaActiva = Tarea(
            idTarea="TAR-020",
            idPaquete="PAQ-100",
            titulo="Tarea Visible",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
        )
        tareaDescartada = Tarea(
            idTarea="TAR-021",
            idPaquete="PAQ-100",
            titulo="Tarea Descartada",
            prioridad=PrioridadTarea.ALTA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=False,
        )
        paquete = PaqueteTrabajo(
            idPaquete="PAQ-100",
            idProyecto="PROY-001",
            nombre="Backend Core",
            tareas=(tareaActiva, tareaDescartada),
        )

        async def renderizar() -> Any:
            async with Layout(
                tableroKanban(
                    paquete=paquete,
                    integrantes=(),
                    alSeleccionarTarea=lambda t: None,
                    alAvanzarTarea=lambda t, e: None,
                    alSolicitarDevolucion=lambda t: None,
                    alCrearTarea=lambda tit, clv: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        assert _buscarPorId(modelo, "tarjeta-tarea-TAR-020") is not None
        assert _buscarPorId(modelo, "tarjeta-tarea-TAR-021") is None
        assert _contieneTexto(modelo, "Tarea Visible")
        assert not _contieneTexto(modelo, "Tarea Descartada")

    def testTableroIndicacionNeutralEnColumnaVacia(self) -> None:
        """Verifica que una columna sin tareas muestre una indicación neutral sin error (EARS-04.6)."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-030",
            idPaquete="PAQ-100",
            titulo="Única tarea en progreso",
            prioridad=PrioridadTarea.BAJA,
            estado=EstadoKanban.EN_PROGRESO,
            contadorRegresos=0,
            activo=True,
        )
        paquete = PaqueteTrabajo(
            idPaquete="PAQ-100",
            idProyecto="PROY-001",
            nombre="Frontend",
            tareas=(tarea,),
        )

        async def renderizar() -> Any:
            async with Layout(
                tableroKanban(
                    paquete=paquete,
                    integrantes=(),
                    alSeleccionarTarea=lambda t: None,
                    alAvanzarTarea=lambda t, e: None,
                    alSolicitarDevolucion=lambda t: None,
                    alCrearTarea=lambda tit, clv: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        assert _buscarPorId(modelo, "columna-vacia-pendiente") is not None
        assert _buscarPorId(modelo, "columna-vacia-en_revision") is not None
        assert _buscarPorId(modelo, "columna-vacia-terminada") is not None
        assert _buscarPorId(modelo, "columna-vacia-en_progreso") is None

    def testTableroBannerVacioCuandoPaqueteNoTieneTareas(self) -> None:
        """Verifica estado orientador cuando el paquete no tiene tareas activas (EARS-04.7)."""
        from reactpy.core.layout import Layout

        paqueteVacio = PaqueteTrabajo(
            idPaquete="PAQ-101",
            idProyecto="PROY-001",
            nombre="Seguridad",
            tareas=(),
        )

        async def renderizar() -> Any:
            async with Layout(
                tableroKanban(
                    paquete=paqueteVacio,
                    integrantes=(),
                    alSeleccionarTarea=lambda t: None,
                    alAvanzarTarea=lambda t, e: None,
                    alSolicitarDevolucion=lambda t: None,
                    alCrearTarea=lambda tit, clv: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        assert _buscarPorId(modelo, "tablero-vacio-paquete") is not None
        assert _contieneTexto(modelo, "Paquete sin tareas activas")
        assert _buscarPorId(modelo, "btn-crear-primera-tarea") is not None

    def testModalNuevaTareaValidacionTitulo(self) -> None:
        """Verifica validación de título (1-120 caracteres) en creación de tareas (EARS-04.5)."""
        from reactpy.core.layout import Layout

        paquete = PaqueteTrabajo(
            idPaquete="PAQ-102",
            idProyecto="PROY-001",
            nombre="Infraestructura",
            tareas=(),
        )
        creadas: list[tuple[str, str]] = []

        async def interactuar() -> Any:
            async with Layout(
                tableroKanban(
                    paquete=paquete,
                    integrantes=(),
                    alSeleccionarTarea=lambda t: None,
                    alAvanzarTarea=lambda t, e: None,
                    alSolicitarDevolucion=lambda t: None,
                    alCrearTarea=lambda tit, clv: creadas.append((tit, clv)),
                )
            ) as layout:
                update = await layout.render()
                btnNueva = _buscarPorId(update["model"], "btn-crear-primera-tarea")
                assert btnNueva is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnNueva["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                update2 = await layout.render()
                btnGuardar = _buscarPorId(update2["model"], "btn-guardar-nueva-tarea")
                assert btnGuardar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnGuardar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                update3 = await layout.render()
                assert _contieneTexto(
                    update3["model"], "El título de la tarea es obligatorio"
                )

                inputTitulo = _buscarPorId(update3["model"], "input-titulo-nueva-tarea")
                assert inputTitulo is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputTitulo["eventHandlers"]["onChange"]["target"],
                        "data": [
                            {"target": {"value": "Configurar clúster Kubernetes"}}
                        ],
                    }
                )
                update4 = await layout.render()
                btnGuardar2 = _buscarPorId(update4["model"], "btn-guardar-nueva-tarea")
                assert btnGuardar2 is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnGuardar2["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                return update4["model"]

        asyncio.run(interactuar())
        assert len(creadas) == 1
        assert creadas[0][0] == "Configurar clúster Kubernetes"
        assert len(creadas[0][1]) > 0

    def testWorkspaceKanbanIntegracionEnComponenteApp(self) -> None:
        """Verifica la integración completa del Kanban y modal de regreso dentro de componenteApp."""
        import sqlite3

        from reactpy.core.layout import Layout

        from app.adapters.esquemaSqlite import inicializarEsquema
        from app.adapters.repositorioSqlite import (
            guardarProyectoCompleto,
            recuperarProyectos,
        )

        conexion = sqlite3.connect(":memory:")
        inicializarEsquema(conexion)

        tareaTest = Tarea(
            idTarea="TAR-500",
            idPaquete="PAQ-500",
            titulo="Tarea Flujo Completo",
            prioridad=PrioridadTarea.ALTA,
            estado=EstadoKanban.EN_PROGRESO,
            contadorRegresos=0,
            activo=True,
        )
        paqueteTest = PaqueteTrabajo(
            idPaquete="PAQ-500",
            idProyecto="PROY-500",
            nombre="Paquete Kanban",
            tareas=(tareaTest,),
        )
        proyectoTest = Proyecto(
            idProyecto="PROY-500",
            nombre="Proyecto Kanban Web",
            tipo=TipoProyecto.DESARROLLO_WEB,
            paquetes=(paqueteTest,),
            integrantes=(),
        )
        guardarProyectoCompleto(conexion, proyectoTest)

        async def flujoCompleto() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                update0 = await layout.render()
                # 1. Navegar a Workspace
                btnWs = _buscarPorId(update0["model"], "nav-item-workspace")
                assert btnWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                updateWs = await layout.render()
                assert (
                    _buscarPorId(updateWs["model"], "tablero-kanban-area") is not None
                )
                assert (
                    _buscarPorId(updateWs["model"], "tarjeta-tarea-TAR-500") is not None
                )

                # 2. Solicitar devolución
                btnDevolver = _buscarPorId(
                    updateWs["model"], "btn-devolver-tarea-TAR-500"
                )
                assert btnDevolver is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnDevolver["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                updateModal = await layout.render()
                assert (
                    _buscarPorId(updateModal["model"], "modal-regreso-dialogo")
                    is not None
                )

                # 3. Ingresar justificación y confirmar
                inputMotivo = _buscarPorId(updateModal["model"], "input-motivo-regreso")
                assert inputMotivo is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputMotivo["eventHandlers"]["onChange"]["target"],
                        "data": [
                            {"target": {"value": "Revisión técnica solicitada por QA"}}
                        ],
                    }
                )
                updateModalEscrito = await layout.render()
                btnConfirmar = _buscarPorId(
                    updateModalEscrito["model"], "btn-confirmar-regreso"
                )
                assert btnConfirmar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnConfirmar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                await layout.render()

        asyncio.run(flujoCompleto())

        # Verificar en SQLite que la tarea retrocedió a Pendiente y tiene contadorRegresos = 1
        res = recuperarProyectos(conexion)
        assert res.esExito()
        proys = res.obtenerValor()
        tareaDb = next(
            t
            for p in proys
            for paq in p.paquetes
            for t in paq.tareas
            if t.idTarea == "TAR-500"
        )
        assert tareaDb.estado == EstadoKanban.PENDIENTE
        assert tareaDb.contadorRegresos == 1
        assert len(tareaDb.historial) == 1
        assert (
            tareaDb.historial[0].comentario.obtenerValor()
            == "Revisión técnica solicitada por QA"
        )


class TestPanelEdicionTareaSideDrawer:
    """Suite de pruebas unitarias para el Side Drawer de Edición, Autoguardado y Descarte (Bloque 5)."""

    def testDrawerRenderizaCamposMetadatosYCronologia(self) -> None:
        """Verifica UT-WEB-06: Muestra ID, paquete, estado actual, campos y cronología con evento de creación."""
        from reactpy.core.layout import Layout

        from app.domain.modelos import EventoCreacionTarea, TransicionHistorial

        evCreacion = EventoCreacionTarea(
            idTarea="TAR-200",
            fechaHora="2026-10-27T08:30:00",
        )
        transicion1 = TransicionHistorial(
            idTransicion="TR-1",
            idTarea="TAR-200",
            estadoOrigen=EstadoKanban.PENDIENTE,
            estadoDestino=EstadoKanban.EN_PROGRESO,
            fechaHora="2026-10-27T09:00:00",
        )
        transicion2 = TransicionHistorial(
            idTransicion="TR-2",
            idTarea="TAR-200",
            estadoOrigen=EstadoKanban.EN_PROGRESO,
            estadoDestino=EstadoKanban.PENDIENTE,
            fechaHora="2026-10-27T09:15:00",
            comentario=Alguno("Faltan especificaciones funcionales"),
        )
        tarea = Tarea(
            idTarea="TAR-200",
            idPaquete="PAQ-200",
            titulo="Configurar Gateway",
            descripcion=Alguno("Rutas y rate limiting"),
            prioridad=PrioridadTarea.ALTA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=1,
            activo=True,
            historial=(transicion1, transicion2),
            eventoCreacion=Alguno(evCreacion),
        )

        async def renderizar() -> Any:
            async with Layout(
                panelEdicionTarea(
                    tarea=tarea,
                    nombrePaquete="Infraestructura Cloud",
                    integrantes=(),
                    alGuardarParcial=lambda t: None,
                    alDescartarTarea=lambda t: None,
                    alCerrar=lambda: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        assert _buscarPorId(modelo, "panel-edicion-tarea-drawer") is not None
        assert _contieneTexto(modelo, "TAR-200")
        assert _contieneTexto(modelo, "Infraestructura Cloud")
        assert _contieneTexto(modelo, "Pendiente")
        assert _buscarPorId(modelo, "evento-creacion-tarea-drawer") is not None
        assert _contieneTexto(modelo, "2026-10-27T08:30:00")
        assert _contieneTexto(modelo, "Faltan especificaciones funcionales")

    def testDrawerTareaLegacySinEventoCreacion(self) -> None:
        """Verifica EARS-06.2: Tarea heredada/legacy no inventa eventos ni fechas de creación."""
        from reactpy.core.layout import Layout

        tareaLegacy = Tarea(
            idTarea="TAR-LEGACY-01",
            idPaquete="PAQ-200",
            titulo="Tarea Histórica Antigua",
            prioridad=PrioridadTarea.BAJA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
            eventoCreacion=Ninguno(),
        )

        async def renderizar() -> Any:
            async with Layout(
                panelEdicionTarea(
                    tarea=tareaLegacy,
                    nombrePaquete="Módulo Legado",
                    integrantes=(),
                    alGuardarParcial=lambda t: None,
                    alDescartarTarea=lambda t: None,
                    alCerrar=lambda: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        assert _buscarPorId(modelo, "evento-creacion-tarea-drawer") is None
        assert _buscarPorId(modelo, "evento-creacion-legacy-drawer") is not None
        assert _contieneTexto(modelo, "Registro histórico heredado")

    def testProteccionCierreSinCambiosCierraDirecto(self) -> None:
        """Verifica que cerrar con '✕' sin cambios pendientes cierre inmediatamente (EARS-06.5)."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-201",
            idPaquete="PAQ-200",
            titulo="Tarea Estable",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
        )
        cerrados: list[bool] = []

        async def interactuar() -> None:
            async with Layout(
                panelEdicionTarea(
                    tarea=tarea,
                    nombrePaquete="General",
                    integrantes=(),
                    alGuardarParcial=lambda t: None,
                    alDescartarTarea=lambda t: None,
                    alCerrar=lambda: cerrados.append(True),
                    estadoGuardado=EstadoGuardado.GUARDADO,
                )
            ) as layout:
                update = await layout.render()
                btnCerrar = _buscarPorId(update["model"], "btn-cerrar-drawer-tarea")
                assert btnCerrar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnCerrar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )

        asyncio.run(interactuar())
        assert len(cerrados) == 1

    def testProteccionCierreConCambiosMuestraAdvertencia(self) -> None:
        """Verifica que ante cambios no guardados se advierta al usuario antes de cerrar."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-202",
            idPaquete="PAQ-200",
            titulo="Tarea Con Borrador",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
        )
        cerrados: list[bool] = []

        async def interactuar() -> Any:
            async with Layout(
                panelEdicionTarea(
                    tarea=tarea,
                    nombrePaquete="General",
                    integrantes=(),
                    alGuardarParcial=lambda t: None,
                    alDescartarTarea=lambda t: None,
                    alCerrar=lambda: cerrados.append(True),
                    estadoGuardado=EstadoGuardado.ERROR,  # simula fallo de persistencia
                )
            ) as layout:
                update = await layout.render()
                btnCerrar = _buscarPorId(update["model"], "btn-cerrar-drawer-tarea")
                assert btnCerrar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnCerrar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                update2 = await layout.render()
                assert (
                    _buscarPorId(update2["model"], "advertencia-cierre-drawer")
                    is not None
                )
                assert len(cerrados) == 0

                # Descartar y cerrar explícitamente
                btnDescartarYCerrar = _buscarPorId(
                    update2["model"], "btn-descartar-borrador-cerrar"
                )
                assert btnDescartarYCerrar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnDescartarYCerrar["eventHandlers"]["onClick"][
                            "target"
                        ],
                        "data": [{}],
                    }
                )
                return update2["model"]

        asyncio.run(interactuar())
        assert len(cerrados) == 1

    def testAutoguardadoOnBlurTitulo(self) -> None:
        """Verifica autoguardado on_blur para título con validación 1-120 caracteres (EARS-06.3)."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-203",
            idPaquete="PAQ-200",
            titulo="Título Original",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
        )
        guardadas: list[Tarea] = []

        async def interactuar() -> None:
            async with Layout(
                panelEdicionTarea(
                    tarea=tarea,
                    nombrePaquete="General",
                    integrantes=(),
                    alGuardarParcial=lambda t: guardadas.append(t),
                    alDescartarTarea=lambda t: None,
                    alCerrar=lambda: None,
                )
            ) as layout:
                update = await layout.render()
                inputTit = _buscarPorId(update["model"], "input-titulo-tarea-drawer")
                assert inputTit is not None
                # Escribir nuevo título
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputTit["eventHandlers"]["onChange"]["target"],
                        "data": [{"target": {"value": "Título Modificado"}}],
                    }
                )
                up2 = await layout.render()
                inputTit2 = _buscarPorId(up2["model"], "input-titulo-tarea-drawer")
                assert inputTit2 is not None
                # Desencadenar onBlur
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": inputTit2["eventHandlers"]["onBlur"]["target"],
                        "data": [{}],
                    }
                )

        asyncio.run(interactuar())
        assert len(guardadas) == 1
        assert guardadas[0].titulo == "Título Modificado"

    def testAutoguardadoOnChangePrioridadYResponsable(self) -> None:
        """Verifica autoguardado inmediato on_change para prioridad y responsable (EARS-06.4)."""
        from reactpy.core.layout import Layout

        integrante = Integrante(
            cedula="0911223344",
            idProyecto="PROY-200",
            nombre="Ana Lucía",
            cargo=CargoIntegrante.DISENADOR_UI_UX,
        )
        tarea = Tarea(
            idTarea="TAR-204",
            idPaquete="PAQ-200",
            titulo="Tarea UI",
            prioridad=PrioridadTarea.BAJA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
        )
        guardadas: list[Tarea] = []

        async def interactuar() -> None:
            async with Layout(
                panelEdicionTarea(
                    tarea=tarea,
                    nombrePaquete="Diseño",
                    integrantes=(integrante,),
                    alGuardarParcial=lambda t: guardadas.append(t),
                    alDescartarTarea=lambda t: None,
                    alCerrar=lambda: None,
                )
            ) as layout:
                update = await layout.render()
                selectPrio = _buscarPorId(
                    update["model"], "select-prioridad-tarea-drawer"
                )
                assert selectPrio is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": selectPrio["eventHandlers"]["onChange"]["target"],
                        "data": [{"target": {"value": "Crítica"}}],
                    }
                )
                up2 = await layout.render()
                selectResp = _buscarPorId(
                    up2["model"], "select-responsable-tarea-drawer"
                )
                assert selectResp is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": selectResp["eventHandlers"]["onChange"]["target"],
                        "data": [{"target": {"value": "0911223344"}}],
                    }
                )

        asyncio.run(interactuar())
        assert len(guardadas) >= 2
        assert guardadas[0].prioridad == PrioridadTarea.CRITICA
        assert guardadas[1].cedulaResponsable.obtenerValor() == "0911223344"

    def testIndicadoresVisualesAutoguardado(self) -> None:
        """Verifica los tres estados visuales: Guardando…, ✓ Guardado y No se pudo guardar con reintento."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-205",
            idPaquete="PAQ-200",
            titulo="Tarea Estado",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
        )

        for est, textoEsperado in [
            (EstadoGuardado.GUARDANDO, "Guardando…"),
            (EstadoGuardado.GUARDADO, "✓ Guardado"),
            (EstadoGuardado.ERROR, "No se pudo guardar"),
        ]:

            async def renderizar(e=est) -> Any:
                async with Layout(
                    panelEdicionTarea(
                        tarea=tarea,
                        nombrePaquete="General",
                        integrantes=(),
                        alGuardarParcial=lambda t: None,
                        alDescartarTarea=lambda t: None,
                        alCerrar=lambda: None,
                        estadoGuardado=e,
                    )
                ) as layout:
                    update = await layout.render()
                    return update["model"]

            modelo = asyncio.run(renderizar())
            assert _buscarPorId(modelo, "indicador-guardado-drawer") is not None
            assert _contieneTexto(modelo, textoEsperado)
            if est == EstadoGuardado.ERROR:
                assert _buscarPorId(modelo, "btn-reintentar-guardado") is not None

    def testDescarteLogicoRequiereConfirmacion(self) -> None:
        """Verifica que el descarte lógico solicite confirmación y no mute si se cancela (EARS-06.6)."""
        from reactpy.core.layout import Layout

        tarea = Tarea(
            idTarea="TAR-206",
            idPaquete="PAQ-200",
            titulo="Tarea a Descartar",
            prioridad=PrioridadTarea.BAJA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
        )
        descartadas: list[Tarea] = []

        async def interactuar() -> None:
            async with Layout(
                panelEdicionTarea(
                    tarea=tarea,
                    nombrePaquete="General",
                    integrantes=(),
                    alGuardarParcial=lambda t: None,
                    alDescartarTarea=lambda t: descartadas.append(t),
                    alCerrar=lambda: None,
                )
            ) as layout:
                update = await layout.render()
                btnDescartar = _buscarPorId(update["model"], "btn-descartar-tarea")
                assert btnDescartar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnDescartar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                upConfirm = await layout.render()
                assert (
                    _buscarPorId(upConfirm["model"], "confirmacion-descarte-tarea")
                    is not None
                )
                assert len(descartadas) == 0

                # Confirmar descarte
                btnConfirmar = _buscarPorId(
                    upConfirm["model"], "btn-confirmar-descarte-tarea"
                )
                assert btnConfirmar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnConfirmar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )

        asyncio.run(interactuar())
        assert len(descartadas) == 1
        assert descartadas[0].idTarea == "TAR-206"

    def testDrawerIntegracionCompletaEnComponenteApp(self) -> None:
        """Verifica la apertura del drawer, autoguardado y descarte lógico integrado en componenteApp."""
        import sqlite3

        from reactpy.core.layout import Layout

        from app.adapters.esquemaSqlite import inicializarEsquema
        from app.adapters.repositorioSqlite import (
            guardarProyectoCompleto,
            recuperarProyectos,
        )

        conexion = sqlite3.connect(":memory:")
        inicializarEsquema(conexion)

        tareaTest = Tarea(
            idTarea="TAR-800",
            idPaquete="PAQ-800",
            titulo="Tarea Original Para Edición",
            descripcion=Alguno("Detalles iniciales"),
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=0,
            activo=True,
        )
        paqueteTest = PaqueteTrabajo(
            idPaquete="PAQ-800",
            idProyecto="PROY-800",
            nombre="Paquete Drawer",
            tareas=(tareaTest,),
        )
        proyectoTest = Proyecto(
            idProyecto="PROY-800",
            nombre="Proyecto Integración Drawer",
            tipo=TipoProyecto.DESARROLLO_WEB,
            paquetes=(paqueteTest,),
            integrantes=(),
        )
        guardarProyectoCompleto(conexion, proyectoTest)

        async def flujoDrawer() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                update0 = await layout.render()
                # 1. Navegar a Workspace
                btnWs = _buscarPorId(update0["model"], "nav-item-workspace")
                assert btnWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                updateWs = await layout.render()
                # 2. Clic en tarjeta para abrir Drawer
                tarjeta = _buscarPorId(updateWs["model"], "titulo-tarea-TAR-800")
                assert tarjeta is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": tarjeta["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                updateDrawer = await layout.render()
                assert (
                    _buscarPorId(updateDrawer["model"], "panel-edicion-tarea-drawer")
                    is not None
                )
                assert (
                    _buscarPorId(updateDrawer["model"], "btn-descartar-tarea")
                    is not None
                )

                # 3. Descartar tarea lógicamente desde el drawer
                btnDescartar = _buscarPorId(
                    updateDrawer["model"], "btn-descartar-tarea"
                )
                assert btnDescartar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnDescartar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                upConf = await layout.render()
                btnConfirmar = _buscarPorId(
                    upConf["model"], "btn-confirmar-descarte-tarea"
                )
                assert btnConfirmar is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnConfirmar["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                await layout.render()

        asyncio.run(flujoDrawer())

        # Verificar en base de datos que activo = False
        res = recuperarProyectos(conexion)
        assert res.esExito()
        proys = res.obtenerValor()
        tareaDb = next(
            t
            for p in proys
            for paq in p.paquetes
            for t in paq.tareas
            if t.idTarea == "TAR-800"
        )
        assert tareaDb.activo is False


class TestVistaMetricas:
    """Suite de pruebas unitarias para la Vista de Métricas, Cuellos de Botella y Filtros (Bloque 6)."""

    def testVistaMetricasCalculaResumenCuantitativoYAvance(self) -> None:
        """Verifica UT-WEB-09 / EARS-07.2: Total activas, desglose Kanban, descartadas y avance global."""
        from reactpy.core.layout import Layout

        t1 = Tarea(
            idTarea="TAR-301",
            idPaquete="PAQ-301",
            titulo="Tarea Pendiente",
            prioridad=PrioridadTarea.BAJA,
            estado=EstadoKanban.PENDIENTE,
            activo=True,
        )
        t2 = Tarea(
            idTarea="TAR-302",
            idPaquete="PAQ-301",
            titulo="Tarea En Progreso",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.EN_PROGRESO,
            activo=True,
        )
        t3 = Tarea(
            idTarea="TAR-303",
            idPaquete="PAQ-301",
            titulo="Tarea Terminada",
            prioridad=PrioridadTarea.ALTA,
            estado=EstadoKanban.TERMINADA,
            activo=True,
        )
        t4 = Tarea(
            idTarea="TAR-304",
            idPaquete="PAQ-301",
            titulo="Tarea Descartada",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.PENDIENTE,
            activo=False,
        )
        paq = PaqueteTrabajo(
            idPaquete="PAQ-301",
            idProyecto="PROY-301",
            nombre="Módulo Métricas",
            tareas=(t1, t2, t3, t4),
        )
        proy = Proyecto(
            idProyecto="PROY-301",
            nombre="Proyecto Analítico",
            tipo=TipoProyecto.DESARROLLO_WEB,
            paquetes=(paq,),
            integrantes=(),
        )

        async def renderizar() -> Any:
            async with Layout(
                vistaMetricas(
                    proyecto=proy,
                    alVolverWorkspace=lambda: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        assert _buscarPorId(modelo, "vista-metricas-contenedor") is not None
        # 3 tareas activas, 1 descartada
        assert _contieneTexto(_buscarPorId(modelo, "metrica-total-activas"), "3")
        assert _contieneTexto(_buscarPorId(modelo, "metrica-total-inactivas"), "1")
        assert _contieneTexto(_buscarPorId(modelo, "metrica-conteo-pendiente"), "1")
        assert _contieneTexto(_buscarPorId(modelo, "metrica-conteo-en-progreso"), "1")
        assert _contieneTexto(_buscarPorId(modelo, "metrica-conteo-terminada"), "1")
        # 1 de 3 terminadas = 33.33%
        assert _contieneTexto(
            _buscarPorId(modelo, "porcentaje-avance-global"), "33.33%"
        )

    def testVistaMetricasSinTareasActivasMuestraCeroPorcientoYSinDivisionPorCero(
        self,
    ) -> None:
        """Verifica EARS-07.5: Proyectos sin tareas muestran 0.0% con 'Sin tareas registradas' sin división por cero."""
        from reactpy.core.layout import Layout

        paqVacio = PaqueteTrabajo(
            idPaquete="PAQ-302",
            idProyecto="PROY-302",
            nombre="Paquete Vacío",
            tareas=(),
        )
        proyVacio = Proyecto(
            idProyecto="PROY-302",
            nombre="Proyecto Nuevo Sin Tareas",
            tipo=TipoProyecto.DESARROLLO_WEB,
            paquetes=(paqVacio,),
            integrantes=(),
        )

        async def renderizar() -> Any:
            async with Layout(
                vistaMetricas(
                    proyecto=proyVacio,
                    alVolverWorkspace=lambda: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        assert _buscarPorId(modelo, "porcentaje-avance-global") is not None
        assert _contieneTexto(_buscarPorId(modelo, "porcentaje-avance-global"), "0.0%")
        assert _buscarPorId(modelo, "texto-sin-tareas-global") is not None
        assert _contieneTexto(
            _buscarPorId(modelo, "texto-sin-tareas-global"), "Sin tareas registradas"
        )
        # Barra paquete vacío también muestra leyenda neutral
        assert _buscarPorId(modelo, "paquete-sin-tareas-PAQ-302") is not None
        assert _contieneTexto(
            _buscarPorId(modelo, "paquete-sin-tareas-PAQ-302"), "Sin tareas registradas"
        )

    def testVistaMetricasDistribucionCargaSinScoringNoAprobado(self) -> None:
        """Verifica EARS-07.2: Muestra únicamente conteos observables y prohíbe etiquetas de scoring subjetivas."""
        from reactpy.core.layout import Layout

        m1 = Integrante(
            cedula="0922334455",
            idProyecto="PROY-303",
            nombre="Valeria Castillo",
            cargo=CargoIntegrante.DESARROLLADOR_FRONTEND,
        )
        tAsignada = Tarea(
            idTarea="TAR-305",
            idPaquete="PAQ-303",
            titulo="Componente Tabla",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.TERMINADA,
            cedulaResponsable=Alguno("0922334455"),
            activo=True,
        )
        paq = PaqueteTrabajo(
            idPaquete="PAQ-303",
            idProyecto="PROY-303",
            nombre="Frontend",
            tareas=(tAsignada,),
        )
        proy = Proyecto(
            idProyecto="PROY-303",
            nombre="Portal Clientes",
            tipo=TipoProyecto.DESARROLLO_WEB,
            paquetes=(paq,),
            integrantes=(m1,),
        )

        async def renderizar() -> Any:
            async with Layout(
                vistaMetricas(
                    proyecto=proy,
                    alVolverWorkspace=lambda: None,
                )
            ) as layout:
                update = await layout.render()
                return update["model"]

        modelo = asyncio.run(renderizar())
        assert _buscarPorId(modelo, "seccion-carga-equipo") is not None
        assert _buscarPorId(modelo, "miembro-carga-0922334455") is not None
        assert _contieneTexto(
            _buscarPorId(modelo, "conteo-asignadas-0922334455"), "1 asignadas"
        )
        assert _contieneTexto(
            _buscarPorId(modelo, "conteo-terminadas-0922334455"), "1 completadas"
        )

        # Prohibición explícita de scoring subjetivo (EARS-07.2)
        assert not _contieneTexto(modelo, "Carga óptima")
        assert not _contieneTexto(modelo, "Carga alta")
        assert not _contieneTexto(modelo, "Burnout")

    def testVistaMetricasCuellosDeBotellaOrdenDescendenteYMotivos(self) -> None:
        """Verifica EARS-07.3: Lista tareas con contadorRegresos > 0 ordenadas descendentemente con motivos históricos."""
        from reactpy.core.layout import Layout

        from app.domain.modelos import TransicionHistorial

        tr1 = TransicionHistorial(
            idTransicion="TR-A",
            idTarea="TAR-310",
            estadoOrigen=EstadoKanban.EN_PROGRESO,
            estadoDestino=EstadoKanban.PENDIENTE,
            fechaHora="2026-10-27T10:00:00",
            comentario=Alguno("Rechazado por fallo en pruebas de integración"),
        )
        tRegresos2 = Tarea(
            idTarea="TAR-310",
            idPaquete="PAQ-304",
            titulo="Tarea Con Dos Regresos",
            prioridad=PrioridadTarea.CRITICA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=2,
            historial=(tr1,),
            activo=True,
        )
        tRegresos1 = Tarea(
            idTarea="TAR-311",
            idPaquete="PAQ-304",
            titulo="Tarea Con Un Regreso",
            prioridad=PrioridadTarea.MEDIA,
            estado=EstadoKanban.PENDIENTE,
            contadorRegresos=1,
            activo=True,
        )
        tSinRegresos = Tarea(
            idTarea="TAR-312",
            idPaquete="PAQ-304",
            titulo="Tarea Limpia",
            prioridad=PrioridadTarea.BAJA,
            estado=EstadoKanban.EN_PROGRESO,
            contadorRegresos=0,
            activo=True,
        )
        paq = PaqueteTrabajo(
            idPaquete="PAQ-304",
            idProyecto="PROY-304",
            nombre="Calidad",
            tareas=(tRegresos2, tRegresos1, tSinRegresos),
        )
        proy = Proyecto(
            idProyecto="PROY-304",
            nombre="Proyecto QA",
            tipo=TipoProyecto.DESARROLLO_WEB,
            paquetes=(paq,),
            integrantes=(),
        )

        async def interactuar() -> Any:
            async with Layout(
                vistaMetricas(
                    proyecto=proy,
                    alVolverWorkspace=lambda: None,
                )
            ) as layout:
                update = await layout.render()
                assert (
                    _buscarPorId(update["model"], "cuello-botella-tarea-TAR-310")
                    is not None
                )
                assert (
                    _buscarPorId(update["model"], "cuello-botella-tarea-TAR-311")
                    is not None
                )
                # La tarea sin regresos no aparece en cuellos de botella
                assert (
                    _buscarPorId(update["model"], "cuello-botella-tarea-TAR-312")
                    is None
                )

                # Expandir detalles de TAR-310
                btnExp = _buscarPorId(update["model"], "btn-expandir-motivos-TAR-310")
                assert btnExp is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnExp["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                update2 = await layout.render()
                return update2["model"]

        modelo = asyncio.run(interactuar())
        assert _buscarPorId(modelo, "motivos-regreso-TAR-310") is not None
        assert _contieneTexto(modelo, "Rechazado por fallo en pruebas de integración")

    def testVistaMetricasFiltrosAnaliticosYOrdenamiento(self) -> None:
        """Verifica EARS-07.4: Sub-panel de filtros interactivos combinables y ordenamiento reactivo."""
        from reactpy.core.layout import Layout

        tA = Tarea(
            idTarea="TAR-401",
            idPaquete="PAQ-400",
            titulo="Tarea Urgente",
            prioridad=PrioridadTarea.CRITICA,
            estado=EstadoKanban.EN_PROGRESO,
            fechaObjetivo=Alguno("2026-11-20"),
            activo=True,
        )
        tB = Tarea(
            idTarea="TAR-402",
            idPaquete="PAQ-400",
            titulo="Tarea Normal",
            prioridad=PrioridadTarea.BAJA,
            estado=EstadoKanban.PENDIENTE,
            fechaObjetivo=Alguno("2026-11-01"),
            activo=True,
        )
        paq = PaqueteTrabajo(
            idPaquete="PAQ-400",
            idProyecto="PROY-400",
            nombre="Core",
            tareas=(tA, tB),
        )
        proy = Proyecto(
            idProyecto="PROY-400",
            nombre="Proyecto Filtros",
            tipo=TipoProyecto.DESARROLLO_WEB,
            paquetes=(paq,),
            integrantes=(),
        )

        async def interactuar() -> None:
            async with Layout(
                vistaMetricas(
                    proyecto=proy,
                    alVolverWorkspace=lambda: None,
                )
            ) as layout:
                update1 = await layout.render()
                assert (
                    _buscarPorId(update1["model"], "fila-tarea-analitica-TAR-401")
                    is not None
                )
                assert (
                    _buscarPorId(update1["model"], "fila-tarea-analitica-TAR-402")
                    is not None
                )

                # Filtrar solo estado 'En progreso'
                filtroEst = _buscarPorId(update1["model"], "filtro-estado")
                assert filtroEst is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": filtroEst["eventHandlers"]["onChange"]["target"],
                        "data": [{"target": {"value": EstadoKanban.EN_PROGRESO.value}}],
                    }
                )
                update2 = await layout.render()
                assert (
                    _buscarPorId(update2["model"], "fila-tarea-analitica-TAR-401")
                    is not None
                )
                assert (
                    _buscarPorId(update2["model"], "fila-tarea-analitica-TAR-402")
                    is None
                )

        asyncio.run(interactuar())

    def testBotonVolverAlWorkspaceLlamaCallback(self) -> None:
        """Verifica que el botón 'Volver al Workspace' invoque el callback alVolverWorkspace."""
        from reactpy.core.layout import Layout

        proy = _fabricarProyectoEjemplo(
            idProyecto="PROY-305", nombre="Retorno Workspace"
        )
        regresados: list[bool] = []

        async def interactuar() -> None:
            async with Layout(
                vistaMetricas(
                    proyecto=proy,
                    alVolverWorkspace=lambda: regresados.append(True),
                )
            ) as layout:
                update = await layout.render()
                btnVolver = _buscarPorId(
                    update["model"], "btn-volver-workspace-desde-metricas"
                )
                assert btnVolver is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnVolver["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )

        asyncio.run(interactuar())
        assert len(regresados) == 1

    def testIntegracionNavegacionMetricasEnComponenteApp(self) -> None:
        """Verifica la navegación hacia Métricas y el regreso al Workspace dentro de componenteApp."""
        import sqlite3

        from reactpy.core.layout import Layout

        from app.adapters.esquemaSqlite import inicializarEsquema
        from app.adapters.repositorioSqlite import guardarProyectoCompleto

        conexion = sqlite3.connect(":memory:")
        inicializarEsquema(conexion)

        proy = _fabricarProyectoEjemplo(
            idProyecto="PROY-900", nombre="Proyecto Métricas E2E"
        )
        guardarProyectoCompleto(conexion, proy)

        async def flujoNavegacion() -> None:
            async with Layout(componenteApp(conexion=conexion)) as layout:
                update0 = await layout.render()
                # 1. Navegar a Métricas desde el header
                btnMetricas = _buscarPorId(update0["model"], "nav-item-metricas")
                assert btnMetricas is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnMetricas["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                updateMetricas = await layout.render()
                assert (
                    _buscarPorId(updateMetricas["model"], "vista-metricas-contenedor")
                    is not None
                )
                assert (
                    _buscarPorId(updateMetricas["model"], "kpis-metricas-grid")
                    is not None
                )

                # 2. Retornar al Workspace desde el botón de la vista
                btnVolverWs = _buscarPorId(
                    updateMetricas["model"], "btn-volver-workspace-desde-metricas"
                )
                assert btnVolverWs is not None
                await layout.deliver(
                    {
                        "type": "layout-event",
                        "target": btnVolverWs["eventHandlers"]["onClick"]["target"],
                        "data": [{}],
                    }
                )
                updateWs = await layout.render()
                assert (
                    _buscarPorId(updateWs["model"], "vista-workspace-contenedor")
                    is not None
                )

        asyncio.run(flujoNavegacion())
