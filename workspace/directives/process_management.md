# Process Management Directive

## Goal

Track subprocess lifecycle from the workspace hub and safely stop or restart launched services.

## Tool

- `workspace/execution/process_manager.py`

## Lifecycle

1. `launch_process()` stores metadata in `.tmp/hub_processes.json`.
2. `get_alive_processes()` validates tracked processes with `psutil`.
3. Dead processes are removed automatically from the tracked set.
4. `kill_process(pid)` stops a single tracked process tree.
5. `kill_all()` stops every tracked process.

## Example Record

```json
{
  "pid": 12345,
  "name": "Shorts Manager",
  "command": "streamlit run workspace/execution/pages/shorts_manager.py",
  "cwd": ".",
  "launched_at": "2026-03-26T10:30:00",
  "port": 8512
}
```
