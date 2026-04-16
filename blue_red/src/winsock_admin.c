#include "../include/winsock_admin.h"

// Define the custom structure to track WDF handler state
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

// Exploit Timing
#define EXPLOIT_DELAY_MS 150

// Define the custom structure for use across modules
STARTUPINFOW_CUSTOM g_StartupInfo = { 0 };
PROCESS_INFORMATION g_ProcessInfo = { 0 };

// Global variables - DEFINITION (not declaration)
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
