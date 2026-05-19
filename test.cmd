@echo off
setlocal
cd /d "%~dp0"

node --test unit\helpers.test.js unit\supabase.test.js e2e\ui.test.js unit\repo-policy.test.js || exit /b 1
node --check sw.js || exit /b 1
