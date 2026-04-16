// include/winsock_admin.c
#include "../include/winsock_admin.h"

// Global variables - DEFINE them here (only once in one file)
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

    // Open Process Token
    bResult = OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &hToken);
    if (bResult) {
        // Get Token Information
        bResult = GetTokenInformation(hToken, TokenElevationType, (LPVOID)&bIsAdmin, sizeof(DWORD), &cbNeeded);
        if (bResult) {
            // Check Elevation Type (2 = Full Elevation/ADMIN)
            CloseHandle(hToken);
            return (bIsAdmin == 2);
        }
        CloseHandle(hToken);
    }
    return FALSE;
}
