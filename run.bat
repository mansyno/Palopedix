@echo off
echo Starting Palopedix...
call conda activate base
cd ui
npm run dev
pause
