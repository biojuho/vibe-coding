# Legacy Manual Tests

This directory stores legacy test scripts that require manual execution.

## Purpose
- Preserve historical diagnostics and exploratory checks.
- Keep unstable or environment-dependent scripts available for manual validation.

## Why excluded from default pytest
- These files require network access, local desktop app control, microphone input, or archived paths.
- They are not deterministic unit tests and can fail in clean CI/local automation.
- Default quality gate must run only reproducible automated tests.

## Typical prerequisites
- Network connectivity for remote API calls.
- Local desktop environment for app-launch checks.
- Audio input device for STT checks.
- Legacy project paths/modules (for archived personal-agent scripts).

## How to run manually
Use explicit file execution or targeted pytest invocation when needed, for example:

```powershell
venv\Scripts\python.exe tests\legacy_manual\manual_api.py
venv\Scripts\python.exe tests\legacy_manual\manual_stt.py
venv\Scripts\python.exe -m pytest -q tests\legacy_manual\manual_desktop_robustness.py
```
