# PowerShell script to start the load balancer demo
# This script starts test backend servers and the load balancer

Write-Host "=== Load Balancer Demo Setup ===" -ForegroundColor Green
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python version: $pythonVersion" -ForegroundColor Blue
} catch {
    Write-Host "Error: Python not found. Please install Python 3.8 or higher." -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install flask requests

# Start test servers in background
Write-Host "Starting test backend servers..." -ForegroundColor Yellow
$servers = @(
    @{Name="TestServer1"; Port=8001},
    @{Name="TestServer2"; Port=8002},
    @{Name="TestServer3"; Port=8003}
)

$jobs = @()
foreach ($server in $servers) {
    $job = Start-Job -ScriptBlock {
        param($port, $name)
        python tests/test_servers.py --single $port
    } -ArgumentList $server.Port, $server.Name -Name "Server-$($server.Port)"
    $jobs += $job
    Write-Host "Started $($server.Name) on port $($server.Port)" -ForegroundColor Green
}

# Wait a moment for servers to start
Start-Sleep -Seconds 2

# Check if servers are running
Write-Host "Checking server status..." -ForegroundColor Yellow
foreach ($server in $servers) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($server.Port)/health" -TimeoutSec 5 -UseBasicParsing
        Write-Host "✓ $($server.Name) is running (Status: $($response.StatusCode))" -ForegroundColor Green
    } catch {
        Write-Host "✗ $($server.Name) failed to start" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Starting Load Balancer ===" -ForegroundColor Green
Write-Host "The load balancer will be available at http://localhost:8080" -ForegroundColor Blue
Write-Host "Press Ctrl+C to stop everything" -ForegroundColor Yellow
Write-Host ""

# Start the load balancer
try {
    python start.py
} catch {
    Write-Host "Load balancer stopped" -ForegroundColor Yellow
} finally {
    # Clean up background jobs
    Write-Host "Stopping test servers..." -ForegroundColor Yellow
    foreach ($job in $jobs) {
        Stop-Job $job -PassThru | Remove-Job
    }
    Write-Host "Demo cleanup complete" -ForegroundColor Green
}
