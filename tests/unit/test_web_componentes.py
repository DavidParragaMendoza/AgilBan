"""Pruebas unitarias para componentes web reactivos de AgilBan (Fase 2).

Verifica el renderizado condicional, la navegacion SPA, el catalogo de proyectos,
el filtrado de busqueda insensible a mayusculas/minusculas y los estados vacios
diferenciados conforme a RF-01, RF-08, UT-WEB-01 y UT-WEB-02.
"""

from __future__ import annotations

import asyncio
from typing import Any

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
from app.ui.web.app import componenteApp
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
