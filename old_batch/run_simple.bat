@echo off
powershell -ExecutionPolicy Bypass -Command "Write-Host \"これはテストです\" -ForegroundColor Green; python --version; Read-Host \"Enterキーを押して終了\""
