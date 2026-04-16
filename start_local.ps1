# Start Local PR Review Environment
# Launches the FastAPI backend and the Next.js dashboard on Windows.

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-FreePort {
    param([int[]]$Candidates)

    foreach ($port in $Candidates) {
        $listener = $null
        try {
            $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
            $listener.Start()
            return $port
        } catch {
            continue
        } finally {
            if ($listener) {
                $listener.Stop()
            }
        }
    }

    throw "No free port found in: $($Candidates -join ', ')"
}

$backendPort = Get-FreePort @(8000, 8001, 8002, 8010)
$frontendPort = Get-FreePort @(3000, 3001, 3002, 3010)
$backendUrl = "http://127.0.0.1:$backendPort"
$dashboardUrl = "http://localhost:$frontendPort"

Write-Host "Starting FastAPI backend on $backendUrl ..." -ForegroundColor Cyan
Start-Process powershell -WorkingDirectory $root -ArgumentList "-NoExit", "-Command", "python -m uvicorn server.app:app --host 0.0.0.0 --port $backendPort"

Write-Host "Starting Next.js dashboard on $dashboardUrl ..." -ForegroundColor Green
$frontendCommand = "`$env:ENV_BASE_URL='$backendUrl'; npm.cmd run dev -- -p $frontendPort"
Start-Process powershell -WorkingDirectory (Join-Path $root "pr_review_dashboard") -ArgumentList "-NoExit", "-Command", $frontendCommand

Write-Host "Open $dashboardUrl in your browser." -ForegroundColor Yellow
