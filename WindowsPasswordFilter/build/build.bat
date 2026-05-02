@echo off

echo Checking for Npcap...

REM Check registry key (Npcap install check)
reg query "HKLM\Software\Npcap" >nul 2>&1
if %errorlevel% neq 0 (
    echo Npcap not found!
    echo Please install Npcap from:
    echo https://npcap.com
    pause
    exit /b
)

echo Compiling...
cl dns_sniffer.c /Fe:dns_sniffer.exe /link wpcap.lib ws2_32.lib

echo Done.