@echo off
echo Publishing Week topics to GitHub...
git add topics.txt
git commit -m "Week topics - %date%"
git push origin main
echo.
echo Done! VPS will pull this automatically on Sunday 6am IST.
pause
