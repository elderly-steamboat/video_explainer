# Streamlit Dashboard — Design Spec
**Date:** 2026-06-10

## Overview

A Streamlit web UI for the video_explainer pipeline. Runs locally alongside the existing CLI. Two-column layout: sidebar (project list, nav) + main area (pipeline step control, output viewer, live logs). No database — filesystem + per-project `state.json` for persistence.

---

## Architecture

```
streamlit run ui/app.py
       │
       ├── reads/writes  projects/<name>/state.json   (step status + artifacts)
       ├── calls         .venv/Scripts/python -m src.cli <step> <project>  (subprocess)
       └── reads         projects/<name>/{script,narration,scenes,...}/    (output files)
```

No FastAPI layer. Streamlit calls the existing CLI via `subprocess.Popen` with stdout/stderr streamed into the live log strip. No new Python modules in `src/` — the UI is purely a wrapper.

---

## File Layout

```
ui/
├── app.py              # Streamlit entrypoint
├── state.py            # read/write state.json per project
├── runner.py           # subprocess wrapper, streams output
└── components/
    ├── sidebar.py      # project list, new project, nav links
    ├── pipeline.py     # pill row + active step card
    ├── output.py       # artifact viewer (per-step)
    └── log.py          # live log strip
```

---

## Layout

### Top bar
- App name ("video explainer") left-aligned
- "local" badge (confirms no cloud dependency)

### Sidebar (200px, `#040404`)
- Section label: PROJECTS
- Clickable project rows — active highlighted with left border in `#c9b8ff`
- Each row: project name + `<current step> · <status>`
- "+ new project" button → text input → calls `python -m src.cli create <name>`
- Bottom links: Settings (opens settings panel in main area), Remotion Studio ↗ (opens `http://localhost:3000` in browser)

### Main area
**Pipeline pill row** — one pill per step in order:
```
Script → Narration → Scenes → Voiceover → Storyboard → Render
```
Colors from `state.json`:
- `done` → lavender (`#c9b8ff`) or mint (`#b8f0c8`) with tick
- active (first non-done step) → peach (`#f9c784`), bold
- `failed` → soft red (`#ffb3b3`)
- `pending` → dimmed (`#333`)

Clicking a completed pill → jump to that step's output card.

**Active step card**
- Step name in peach, uppercase, no emoji
- Short description of what the step does + which CLI command it maps to
- Options relevant to that step (see per-step options below)
- "Run" button (peach bg, black text) + "Run all remaining" (dark bg, muted)
- On run: button shows spinner, log strip activates, pill turns to running state

**Output card (per step)**
- Shows when step is `done`
- Header: step name + "done" in mint + "view →" link (opens artifact in OS default app)
- Body: artifact summary (e.g. "4 narrations · projects/hash-functions/narration/")
- If `failed`: shows error message from `state.json` in soft red

**Log strip**
- Monospace font, black bg, dim green text when idle, bright green when running
- Last ~10 lines of subprocess stdout/stderr
- Expandable to full log view

---

## Per-Step Options

| Step | Options |
|---|---|
| Script | LLM provider (claude-code / mock), duration (60s/120s/180s/300s) |
| Narration | — (no options) |
| Scenes | Resolution (see below), force regen toggle |
| Voiceover | TTS provider (edge / mock), voice (edge voice list) |
| Storyboard | — |
| Render | Resolution, encoding (fast / default / slow), concurrency |

**Resolution presets:**

| Label | Dimensions | Use case |
|---|---|---|
| 4K | 3840×2160 | YouTube final |
| 1080p | 1920×1080 | Default |
| 720p | 1280×720 | Dev/preview |
| Vertical 1080 | 1080×1920 | Shorts / Reels / TikTok |
| Vertical 720 | 720×1280 | Shorts preview |

---

## State Management

Each project has `projects/<name>/state.json`:

```json
{
  "script": {
    "status": "done",
    "completed_at": "2026-06-10T21:00:00Z",
    "artifacts": ["projects/hash-functions/script/script.json"],
    "error": null
  },
  "narration": {
    "status": "done",
    "completed_at": "2026-06-10T21:05:00Z",
    "artifacts": [
      "projects/hash-functions/narration/scene_01.json",
      "projects/hash-functions/narration/scene_02.json"
    ],
    "error": null
  },
  "scenes": {
    "status": "failed",
    "completed_at": "2026-06-10T21:10:00Z",
    "artifacts": [],
    "error": "Validation errors: Undefined variable: 'floodOpacity'"
  },
  "voiceover":  { "status": "pending", "completed_at": null, "artifacts": [], "error": null },
  "storyboard": { "status": "pending", "completed_at": null, "artifacts": [], "error": null },
  "render":     { "status": "pending", "completed_at": null, "artifacts": [], "error": null }
}
```

`status` values: `pending` | `running` | `done` | `failed`

`state.py` responsibilities:
- `load(project)` → dict
- `set_running(project, step)`
- `set_done(project, step, artifacts)`
- `set_failed(project, step, error)`
- Derives artifact list by scanning the relevant output directory on `set_done`

**On UI load:** if a step is `running` but no process is alive (detected by checking PID or absence of lock file), reset to `failed` with error "Process interrupted — re-run."

**Backwards compat:** if `state.json` missing, derive status from filesystem (check if expected output files exist) and write a fresh `state.json`.

---

## Settings Panel

Opened from sidebar "Settings" link. Renders in main area instead of the pipeline view. Shows and edits `config.yaml`:
- LLM provider + model
- TTS provider + voice_id
- Video resolution + fps
- Review checkpoints (toggles)

Saves on "Apply" — writes `config.yaml` directly.

---

## New Project Flow

1. User clicks "+ new project" in sidebar
2. Text input appears inline
3. On submit: runs `python -m src.cli create <name>` via subprocess
4. Creates `projects/<name>/state.json` with all steps `pending`
5. Sidebar refreshes, new project selected, main area shows Script step ready

---

## Running the UI

```bash
# from repo root, venv active
pip install streamlit
streamlit run ui/app.py
# opens http://localhost:8501
```

Single command, no separate server. Streamlit hot-reloads on file save.

---

## Out of Scope

- Auth (local tool, no auth needed)
- Multiple simultaneous project runs (one subprocess at a time per project)
- Remotion Studio embedded in the UI (link out to `localhost:3000` instead)
- Refine / factcheck / feedback steps (add in v2)
- Sound design steps (add in v2)
