@echo off
setlocal
cd /d "%~dp0"

rem Uso: rodar.bat            (carga normal/incremental)
rem      rodar.bat --desde 2026-01-01
rem      rodar.bat testes     (roda os testes)

set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
    set "BASE="
    where py >nul 2>nul && set "BASE=py"
    if not defined BASE where python >nul 2>nul && set "BASE=python"
    if not defined BASE (
        echo Python nao encontrado. Instale em https://www.python.org/downloads/ marcando "Add python.exe to PATH".
        goto fim
    )
    echo Criando ambiente virtual...
    call %%BASE%% -m venv .venv || goto erro
)

rem reinstala as dependencias so quando o requirements.txt muda
fc /b requirements.txt ".venv\requirements.instalado" >nul 2>nul
if errorlevel 1 (
    echo Instalando dependencias...
    "%PY%" -m pip install --disable-pip-version-check -q -r requirements.txt || goto erro
    copy /y requirements.txt ".venv\requirements.instalado" >nul
)

if /i "%~1"=="testes" (
    "%PY%" -m pytest
) else (
    "%PY%" pipeline.py %*
)
if errorlevel 1 goto erro
goto fim

:erro
echo.
echo Algo deu errado. Veja a mensagem acima.

:fim
rem pausa so quando aberto com duplo clique, para a janela nao fechar
echo %cmdcmdline% | find /i "/c" >nul && pause
endlocal
