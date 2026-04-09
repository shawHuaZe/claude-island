# Claude Island

Dynamic Island style notification widget for Claude Code on Windows 11.

## Features

- **Dynamic Island Style UI** - Glassmorphism pill that expands on hover
- **Task Status Cards** - Shows processing, completed, and pending tasks
- **Permission Authorization** - Approve/deny tool permissions directly from the widget
- **Auto-expand** - Automatically shows card when user action is needed
- **Click to Jump** - Click anywhere to activate Claude Code terminal
- **Windows 11 Native** - Uses Windows API for proper window activation

## Requirements

- Windows 11
- Node.js 18+ (for Electron)
- Python 3.9+ (for uv)
- Claude Code CLI

## Quick Start

### 1. Clone and Setup

```powershell
git clone https://github.com/shawHuaZe/claude-island.git
cd claude-island
.\setup.ps1
```

This will automatically:
- Install Python dependencies with `uv`
- Install npm dependencies
- Configure Claude Code hooks

### 2. Run

```powershell
.\start.ps1
```

This starts both the backend server and Electron frontend.

### 3. Use

1. Start Claude Code as normal
2. The widget appears as a small pill on the left side of your screen
3. Hover over the pill to see task cards
4. Task completions and permission requests auto-expand the widget

## Scripts

| Script | Description |
|--------|-------------|
| `setup.ps1` | Initial setup (venv, deps, hooks) |
| `start.ps1` | Start backend + frontend |
| `stop.ps1` | Stop all services |

### Script Options

```powershell
# Setup with options
.\setup.ps1 -SkipFrontend  # Skip npm install
.\setup.ps1 -SkipHooks     # Skip hooks configuration

# Start with options
.\start.ps1 -BackendOnly   # Only start backend
.\start.ps1 -FrontendOnly   # Only start frontend
```

## Manual Installation (without scripts)

### Backend
```powershell
cd backend
uv venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

### Frontend
```powershell
cd frontend
npm install
npm start
```

### Manual Hook Configuration

```json
{
  "hooks": [
    { "event": "SessionStart", "url": "http://127.0.0.1:8080/hooks/SessionStart", "async": true },
    { "event": "SessionEnd", "url": "http://127.0.0.1:8080/hooks/SessionEnd", "async": true },
    { "event": "PreToolUse", "url": "http://127.0.0.1:8080/hooks/PreToolUse", "async": true },
    { "event": "PostToolUse", "url": "http://127.0.0.1:8080/hooks/PostToolUse", "async": true },
    { "event": "PermissionRequest", "url": "http://127.0.0.1:8080/hooks/PermissionRequest", "async": true },
    { "event": "Notification", "url": "http://127.0.0.1:8080/hooks/Notification", "async": true }
  ]
}
```

## Usage

| State | Appearance | Action |
|-------|------------|--------|
| Default | Compact pill (64px) | Vertical text + status light + badge |
| Hover | Expanded card panel (340px) | Shows task cards |
| Task Complete | Green card auto-expands | Click to jump to terminal |
| Permission Required | Blue card auto-expands | Approve/Deny buttons |
| Click Outside | Jump to terminal | Activates Claude Code window |

## Project Structure

```
claude-island/
├── setup.ps1         # Setup script (uv + npm + hooks)
├── start.ps1         # Launcher script
├── stop.ps1          # Stop script
├── backend/
│   ├── main.py       # FastAPI server + WebSocket
│   ├── models.py     # Data models
│   ├── terminal.py   # Windows terminal activation
│   └── requirements.txt
├── frontend/
│   ├── main.js      # Electron main process
│   ├── preload.js    # Context bridge
│   ├── index.html    # Widget UI
│   └── package.json
└── hooks/
    └── hooks.json    # Claude Code hooks config
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/hooks/{event}` | Receive Claude Code hook events |
| GET | `/api/sessions` | List all sessions |
| GET | `/api/permissions/pending` | List pending permissions |
| POST | `/api/permissions/{id}/approve` | Approve permission |
| POST | `/api/permissions/{id}/deny` | Deny permission |
| POST | `/api/terminal/activate` | Activate terminal window |
| WS | `/ws` | WebSocket for real-time updates |

## Troubleshooting

### Widget not appearing
- Check if backend is running: `Invoke-WebRequest http://127.0.0.1:8080/health`
- Check Electron console for errors

### Terminal not activating
- Make sure Claude Code terminal window is open
- Check Windows Task Manager for running terminal processes

### Hooks not working
- Verify hooks are in `%USERPROFILE%\.claude\settings.json`
- Check backend is accessible

## License

MIT
