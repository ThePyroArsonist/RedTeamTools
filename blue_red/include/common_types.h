#pragma once

#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Custom structure to track WDF handler state
typedef struct _STARTUPINFOW_CUSTOM {
    DWORD dwSize;
    LPWSTR lpReserved;
    LPWSTR lpReserved0;
    LPWSTR lpTitle;
    LPWSTR lpReserved1;
    LPWSTR lpReserved2;
    LPVOID lpReserved3;
    DWORD wShowWindow;
    LPWSTR lpReserved4;
    DWORD dwX;
    DWORD dwY;
    DWORD dwXSize;
    DWORD dwYSize;
    DWORD dwXPos;
    DWORD dwYPos;
    DWORD dwFlags;
    LPWSTR lpReserved5;
    // Custom extension fields for exploit tracking
    DWORD dwXStartInfo;
    DWORD dwYStartInfo;
    DWORD dwStartInfoFlags;
} STARTUPINFOW_CUSTOM, *PSTARTUPINFOW_CUSTOM;

// Helper functions
void InitializeWinsock(void);
BOOL IsAdmin(void);
