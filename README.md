# Pac-Man con busqueda

Juego de Pac-Man hecho con Python y Tkinter. La GUI muestra dos algoritmos de busqueda mientras se juega:

- A* calcula una ruta sugerida desde Pac-Man hasta el pellet mas cercano.
- BFS calcula las rutas de persecucion de los fantasmas hacia Pac-Man.

## Ejecutar

```powershell
uv run python pacman_search.py
```

En Windows tambien puedes usar el script incluido, que deja el cache, el Python gestionado por `uv` y el entorno virtual del juego dentro del proyecto:

```powershell
.\run_game.ps1
```

## Controles

- Flechas o `WASD`: mover a Pac-Man.
- `H`: mostrar u ocultar la ruta sugerida por A*.
- `G`: mostrar u ocultar las rutas BFS de los fantasmas.
- `Espacio`: pausar o continuar.
- `R`: reiniciar.
