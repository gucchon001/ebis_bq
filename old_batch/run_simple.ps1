# run_simple.ps1
# シンプルなテストスクリプト

# 文字エンコーディングをUTF-8に設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

Write-Host "これはテストです" -ForegroundColor Green
python --version
Read-Host "Enterキーを押して終了" 