# Збирає один файл dist\OBDStudio.exe (без консольного вікна) з іконкою.
# Запуск:  powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Створюю віртуальне середовище .venv..."
    py -3 -m venv .venv
}
& .venv\Scripts\python -m pip install --disable-pip-version-check -q -r requirements-dev.txt

if (-not (Test-Path "obd_studio\resources\icon.ico")) {
    Write-Host "Малюю іконку..."
    & .venv\Scripts\python tools\make_icon.py
}

Write-Host "Запускаю тести..."
& .venv\Scripts\python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Тести не пройшли — збірку зупинено." }

Write-Host "Збираю .exe..."
& .venv\Scripts\pyinstaller --noconfirm --clean --onefile --windowed --name OBDStudio `
    --icon obd_studio\resources\icon.ico `
    --add-data "obd_studio\resources;obd_studio\resources" `
    main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller завершився з помилкою." }

Write-Host "Перевіряю зібраний .exe..."
$env:QT_QPA_PLATFORM = "offscreen"
$p = Start-Process dist\OBDStudio.exe -ArgumentList "--self-test" -Wait -PassThru
Remove-Item Env:QT_QPA_PLATFORM
if ($p.ExitCode -ne 0) { throw "Зібраний .exe не запустився (код $($p.ExitCode))." }

Write-Host "Готово: dist\OBDStudio.exe"
