# PacmanDoom.py

![image](.github/logo.png)

Pac-Man/DOOM-style maze game built with Python and pygame. By default, it opens in classic 2D mode; the `3D Mode` button switches to a raycasting view with a real-time search map:

- A* calculates a suggested path from the player to the nearest pellet.
- A ghost chases the player using Dijkstra.
- The side panel shows explored nodes, the frontier, and the decision tree.
- Dots keep their base color and show rings using the color of the enemy that reached them during the search.
- `+` and `-` change the game speed while playing.
- In 3D mode, arrow keys/WASD are interpreted relative to your first-person view.

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
uv run python -m doom_search
```

## Controls

- Arrow keys or `WASD`: move the player.
- `M` or the corner button: switch between classic mode and 3D mode.
- `+` or `-`: increase or decrease speed.
- `H`: show or hide the A* suggested path.
- `G`: show or hide the ghost's Dijkstra path.
- `T`: show or hide decision tree lines.
- `Space`: pause or resume.
- `R`: restart.

## Structure

- `doom_search/level.py`: map, walls, pellets, and neighbors.
- `doom_search/algorithms.py`: Dijkstra, BFS, A*, and path reconstruction.
- `doom_search/game_state.py`: game rules and search snapshot.
- `doom_search/pygame_app.py`: player view, tactical map, and pygame input.
