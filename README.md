# PY Timeline (offline render, Python clips)
Run with a local server (required for Worker + Pyodide):
python3 -m http.server 8000
Open http://localhost:8000

- Init loads Pyodide + numpy in a Worker
- Play always re-renders then plays
- Render WAV exports
- Double-click a .py clip on the timeline to edit its code
