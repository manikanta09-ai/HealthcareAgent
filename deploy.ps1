# Fully-Automated Windows Server Bootstrap & Deployment Script
# Run this inside PowerShell on your remote Windows EC2 instance.

# Set output preferences
$ErrorActionPreference = "Stop"
Write-Output "=== Starting Windows Server Bootstrap & Deployment ==="

# Helper function to refresh Environment Path variables dynamically
function Refresh-Path {
    Write-Output "Refreshing System environment variables..."
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# 1. Install/Verify Python 3.10
try {
    Get-Command python -ErrorAction Stop > $null
    Write-Output "Found Python: $(python --version)"
} catch {
    Write-Output "Python is not installed. Downloading Python 3.10.11 installer..."
    $pythonUrl = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe"
    $pythonInstaller = "$env:TEMP\python-installer.exe"
    
    # Download
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller
    
    # Silent Installation
    Write-Output "Installing Python 3.10.11 silently... Please wait..."
    Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait
    
    Remove-Item $pythonInstaller
    Refresh-Path
}

# 2. Install/Verify Node.js (Vite 8 requires Node 20.19+ or 22.12+)
try {
    Get-Command node -ErrorAction Stop > $null
    $nodeVersion = node --version
    # Upgrade if Node is v1X, v20 less than v20.19, or v22 less than v22.12
    if (($nodeVersion -match "^v1[0-9]\.") -or ($nodeVersion -match "^v20\.(?:[0-9]|1[0-8])\.") -or ($nodeVersion -match "^v22\.(?:[0-9]|1[0-1])\.")) {
        Write-Warning "Found outdated Node.js ($nodeVersion). Upgrading to Node.js v22..."
        throw "Node.js upgrade required"
    }
    Write-Output "Found Node.js: $nodeVersion"
} catch {
    Write-Output "Downloading Node.js 22.13.1 MSI installer..."
    $nodeUrl = "https://nodejs.org/dist/v22.13.1/node-v22.13.1-x64.msi"
    $nodeInstaller = "$env:TEMP\node-installer.msi"
    
    # Download
    Invoke-WebRequest -Uri $nodeUrl -OutFile $nodeInstaller
    
    # Silent Installation
    Write-Output "Installing Node.js 22.13.1 silently... Please wait..."
    Start-Process msiexec.exe -ArgumentList "/i $nodeInstaller /qn /norestart" -Wait
    
    Remove-Item $nodeInstaller
    Refresh-Path
}

# 3. Install/Verify Ollama & Model
try {
    Get-Command ollama -ErrorAction Stop > $null
    Write-Output "Found Ollama. Checking service..."
} catch {
    Write-Output "Ollama is not installed. Downloading Ollama Setup..."
    $ollamaUrl = "https://ollama.com/download/OllamaSetup.exe"
    $ollamaInstaller = "$env:TEMP\OllamaSetup.exe"
    
    # Download
    Invoke-WebRequest -Uri $ollamaUrl -OutFile $ollamaInstaller
    
    # Silent Installation
    Write-Output "Installing Ollama silently..."
    Start-Process -FilePath $ollamaInstaller -ArgumentList "/SP- /VERYSILENT /NORESTART" -Wait
    
    Remove-Item $ollamaInstaller
    Refresh-Path
    
    # Wait for Ollama process to spawn background service
    Start-Sleep -Seconds 5
}

# Ensure Ollama service is running and start it if not
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -ErrorAction Stop > $null
    Write-Output "Ollama service is active."
} catch {
    Write-Output "Starting Ollama service..."
    # Start Ollama service in background
    Start-Process -FilePath "ollama" -ArgumentList "serve" -NoNewWindow
    Start-Sleep -Seconds 8
}

# Pull required model
Write-Output "Downloading Llama 3.2 3B model (Ollama)... This might take a few minutes..."
ollama pull llama3.2:3b

# 4. Setup Python Backend Virtual Environment
Write-Output "`n--> Configuring Backend..."
Set-Location -Path "backend"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
Set-Location -Path ".."

# 5. Build Frontend Production Assets
Write-Output "`n--> Building Frontend..."
Set-Location -Path "frontend"
# Clean up cached optional dependencies to fix the Rolldown native binding issue
Remove-Item -Path "node_modules", "package-lock.json" -Recurse -Force -ErrorAction SilentlyContinue
npm install
npm run build
Set-Location -Path ".."

# 6. Start the Server
Write-Output "`n=== Bootstrap Complete! ==="
Write-Output "Starting the application on http://0.0.0.0:8080..."
Write-Output "Keep this terminal running."
Set-Location -Path "backend"
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
