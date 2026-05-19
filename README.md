# DOOM Search

Juego de laberinto tipo DOOM hecho con Python y pygame. La izquierda muestra una vista 3D con raycasting y la derecha muestra el mapa de busqueda en tiempo real:

- A* calcula una ruta sugerida desde el jugador hasta el pellet mas cercano.
- Hay dos fantasmas: uno persigue con A* y otro con BFS.
- El panel lateral muestra nodos explorados, frontera y arbol de decision.
- Los dots mantienen su color base y muestran aros con el color del enemigo que los alcanzo durante la busqueda.
- `+` y `-` cambian la velocidad en medio del juego.

## Ejecutar

```powershell
.\run_game.ps1
```

El script deja el cache, el Python gestionado por `uv` y el entorno virtual del juego dentro del proyecto. Usa Python 3.13 para evitar que pygame intente compilarse en Python 3.14.

Si ya tienes el entorno preparado, tambien puedes ejecutar el modulo directamente:

```powershell
uv run python -m doom_search
```

## Controles

- Flechas o `WASD`: mover al jugador.
- `+` o `-`: subir o bajar velocidad.
- `H`: mostrar u ocultar la ruta sugerida por A*.
- `G`: mostrar u ocultar las rutas BFS de los enemigos.
- `T`: mostrar u ocultar lineas del arbol de decision.
- `Espacio`: pausar o continuar.
- `R`: reiniciar.

## Estructura

- `doom_search/level.py`: mapa, paredes, pellets y vecinos.
- `doom_search/algorithms.py`: BFS, A* y reconstruccion de rutas.
- `doom_search/game_state.py`: reglas del juego y snapshot de busqueda.
- `doom_search/pygame_app.py`: vista del jugador, mapa tactico e input con pygame.
