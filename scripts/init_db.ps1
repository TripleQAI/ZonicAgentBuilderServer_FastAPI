# init_db.ps1 — apply db/ to the target database with psql.
#
# The application never runs DDL; it has no database connection to run it on.
# This is the one place schema is applied.
#
#   $env:AGENTBUILDER_DSN = "postgresql://user:pass@localhost:5434/agentworkflowbuilder"
#   .\scripts\init_db.ps1                       # apply schema + seeds
#   .\scripts\init_db.ps1 -Role agentbuilder_app  # also apply grants
#   .\scripts\init_db.ps1 -Drop                 # tear down first

param(
    [string]$Dsn  = $env:AGENTBUILDER_DSN,
    [string]$Role = "",
    [switch]$Drop
)

if (-not $Dsn) {
    Write-Error "Set AGENTBUILDER_DSN or pass -Dsn. Example: postgresql://user:pass@host:5434/agentworkflowbuilder"
    exit 1
}

$db = Join-Path $PSScriptRoot "..\db" | Resolve-Path
Push-Location $db
try {
    if ($Drop) {
        Write-Host "Dropping existing objects..." -ForegroundColor Yellow
        psql $Dsn -v ON_ERROR_STOP=1 -f 999_drop_all.sql
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Write-Host "Applying schema..." -ForegroundColor Cyan
    psql $Dsn -v ON_ERROR_STOP=1 -f run_all.sql
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    if ($Role) {
        Write-Host "Applying grants for role '$Role'..." -ForegroundColor Cyan
        psql $Dsn -v ON_ERROR_STOP=1 -v pgf_role=$Role -f 011_grants.sql
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }

    Write-Host "Done." -ForegroundColor Green
}
finally {
    Pop-Location
}
