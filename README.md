# PYline

[](https://github.com/maetyu-d/PYline-audio-environment/blob/main/Screenshot%202026-02-01%20at%2021.33.56.png)

Run with a local server (required for Worker + Pyodide):
python3 -m http.server 8000
Open http://localhost:8000

- Init loads Pyodide + numpy in a Worker
- Play always re-renders (usually very fast) then plays
- Render WAV exports
- Double-click a .py clip on the timeline to edit its code
