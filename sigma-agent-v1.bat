@echo off
setlocal

REM Scriptin bulunduğu dizini al (Proje Root)
set "PROJECT_ROOT=%~dp0"

REM Python CLI dosyasının yolu
set "CLI_SCRIPT=%PROJECT_ROOT%python-core\cli.py"

REM Komutu çalıştır (artık chat argümanı gerekmiyor)
python "%CLI_SCRIPT%" %*

endlocal