# Pycman

![image](.github/logo.png)

Pycman search game built with Python and pygame. The game uses a classic 2D board with real-time pathfinding overlays:

- Pac-Man calculates the route to the nearest pellet using Dijkstra.
- The ghost chases the player using Dijkstra.
- The board can show explored nodes, the frontier, and the decision tree.
- Dots keep their base color and show rings using the color of the enemy that reached them during the search.
- `+` and `-` change the game speed while playing.

## Running

To install dependencies after cloning the repository:

```powershell
.\install.ps1
```

If Windows blocks PowerShell scripts, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Then run the game:

```powershell
.\run_game.ps1
```

The script keeps the cache, the `uv`-managed Python install, and the game's virtual environment inside the project. It uses Python 3.13 to avoid pygame trying to compile on Python 3.14.

If the environment is already prepared, you can also run the module directly:

```powershell
uv run python -m pycman
```

## Building a Windows executable

To create a distributable build for people who do not have Python installed:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

The build output is written to:

```text
build\Pycman
```

Send the whole `build\Pycman` folder, not only the `.exe`, because PyInstaller keeps the runtime files and assets beside the executable.

## Controls

- Arrow keys or `WASD`: move the player.
- `+` or `-`: increase or decrease speed.
- `H`: show or hide the Dijkstra suggested path.
- `G`: show or hide the ghost's Dijkstra path.
- `T`: show or hide decision tree lines.
- `Space`: pause or resume.
- `R`: restart.

## Structure

- `pycman/level.py`: map, walls, pellets, and neighbors.
- `pycman/algorithms.py`: Dijkstra pathfinding variants and path reconstruction.
- `pycman/game_state.py`: game rules and search snapshot.
- `pycman/animation.py`: smooth movement between grid cells.
- `pycman/sprites.py`: sprite loading, animation frames, and scale cache.
- `pycman/renderer.py`: classic board, search overlays, sprites, and HUD.
- `pycman/pygame_app.py`: pygame event loop and high-level app coordination.
