$ErrorActionPreference = "Stop"

$repo = "\\wsl.localhost\Ubuntu-24.04\home\a\.openclaw\taskcaptain_xiugai"

Write-Host "Repo: $repo"
Set-Location $repo

git status --short
git log --oneline -1
git push origin main
