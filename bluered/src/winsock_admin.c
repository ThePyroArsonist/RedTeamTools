#pragma once

#include "../include/config.h"
#include "../include/types.h"
#include "../include/winsock_admin.h"

// Global variables for Winsock initialization
WSADATA wsaData;
int wsaInitResult = 0;

// Initialize Winsock function
void InitializeWinsock(void) {
    wsaInitResult = WSAStartup(0x0202, &wsaData);
}

// Check Admin Rights
BOOL IsAdmin(void) {
    HANDLE hToken = NULL;
    DWORD bIsAdmin = 0;
    DWORD cbNeeded = 0;
    BOOL bResult = FALSE;

    bResult = OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &hToken);
    if (bResult) {
        bResult = GetTokenInformation(hToken, TokenElevationType, (LPVOID)&bIsAdmin, sizeof(DWORD), &cbNeeded);
        if (bResult) {
            CloseHandle(hToken);
            return (bIsAdmin == 2);  // ElevationTypeFull
        }
        CloseHandle(hToken);
    }
    return FALSE;
}