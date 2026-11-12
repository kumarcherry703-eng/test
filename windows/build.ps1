$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
py -3 -m venv .venv-build
& .\.venv-build\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& .\.venv-build\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name SetuHost --paths . --add-data 'setu/static;setu/static' --collect-all pyautogui --collect-all uvicorn --collect-all fastapi windows/host.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
Write-Host 'Built dist\SetuHost\SetuHost.exe. Keep all files in that folder together.'
