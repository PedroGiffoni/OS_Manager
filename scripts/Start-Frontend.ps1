$ErrorActionPreference='Stop'
Set-Location (Join-Path (Split-Path $PSScriptRoot) 'frontend')
npm.cmd run dev