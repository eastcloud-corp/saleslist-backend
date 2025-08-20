@echo off
echo Starting Render API Keep-Alive Service...
echo.
echo This will ping the API every 10 minutes to prevent Render from sleeping.
echo Press Ctrl+C to stop the service.
echo.

node keep-alive.js

pause