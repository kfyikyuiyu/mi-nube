@echo off
title Mi Nube - Servidor
cd /d "%~dp0"

echo.
echo  ================================
echo   MI NUBE - Iniciando servidor...
echo  ================================
echo.

:: Activar entorno virtual e iniciar Flask en segundo plano
call venv\Scripts\activate.bat
start "" python app.py

:: Esperar 3 segundos para que Flask arranque
timeout /t 3 /nobreak >nul

:: Iniciar ngrok en segundo plano
start "" "C:\Users\%USERNAME%\Downloads\ngrok.exe" http 5000

:: Esperar 3 segundos para que ngrok genere el tunnel
timeout /t 3 /nobreak >nul

:: Obtener el link de ngrok y abrirlo en el navegador
echo  Obteniendo link de ngrok...
for /f "tokens=*" %%a in ('powershell -command "(Invoke-WebRequest -Uri http://localhost:4040/api/tunnels -UseBasicParsing | ConvertFrom-Json).tunnels[0].public_url"') do set NGROK_URL=%%a

echo.
echo  ================================
echo   Link publico: %NGROK_URL%
echo  ================================
echo.

:: Abrir el link en el navegador
start "" "%NGROK_URL%"

echo  Servidor corriendo. Cierra esta ventana para detenerlo.
echo.
pause
