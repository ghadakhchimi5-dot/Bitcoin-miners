# Launch the presentation app (opens http://localhost:8501 in the browser).
# Usage, from anywhere:  powershell -ExecutionPolicy Bypass -File app\run_app.ps1
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
& "$root\.venv\Scripts\python.exe" -m streamlit run "$root\app\streamlit_app.py"
