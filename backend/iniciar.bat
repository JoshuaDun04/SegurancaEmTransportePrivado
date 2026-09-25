@echo off
chcp 65001 >nul
rem Sobe o servidor de detecção. Na primeira vez cria o ambiente Python (.venv)
rem e instala as dependências; nas próximas só inicia o servidor.
cd /d "%~dp0"

rem Com placa NVIDIA, a instalacao troca o PyTorch de CPU pelo de GPU - CUDA -,
rem que deixa a deteccao varias vezes mais rapida.
if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente Python em backend\.venv ...
    python -m venv .venv || goto :erro
    echo Instalando dependencias ^(pode demorar alguns minutos na primeira vez^) ...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :erro
    where nvidia-smi >nul 2>&1 && (
        echo Placa NVIDIA encontrada: instalando PyTorch com suporte a GPU ^(~3 GB^) ...
        ".venv\Scripts\python.exe" -m pip install --force-reinstall --no-deps torch torchvision --index-url https://download.pytorch.org/whl/cu128 || goto :erro
    )
)

echo.
echo Enderecos para digitar no app (celular na mesma rede Wi-Fi):
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do echo    %%a:8000
echo Com o celular no cabo USB (adb reverse tcp:8000 tcp:8000): localhost:8000
echo Pagina de teste neste PC: http://localhost:8000
echo.

".venv\Scripts\python.exe" -m uvicorn server:app --host 0.0.0.0 --port 8000
goto :eof

:erro
echo.
echo Falhou. Confira se o Python 3.10+ esta instalado e no PATH.
pause
