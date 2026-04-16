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
        printf("[BACKDOOR] Waiting for client...\n");
        printf("[BACKDOOR] Press Ctrl+C to stop.\n");
        fflush(stdout);
        Sleep(5000);  // Keep open so user can see output

        // Now accept connections
        SOCKET client = accept(s, NULL, NULL);
        printf("[DEBUG] accept() returned: %lu\n", (unsigned long)client);
        fflush(stdout);
        
        if (client != INVALID_SOCKET) {
            printf("[BACKDOOR] Client connected from socket handle\n");
            fflush(stdout);
            
            while (TRUE) {
                int bytes = recv(client, hostip, sizeof(hostip) - 1, 0);
                if (bytes > 0) {
                    hostip[bytes] = 0;
                    printf("[BACKDOOR] Received: %s\n", hostip);
                    fflush(stdout);
                } else if (bytes == 0) {
                    printf("[BACKDOOR] Client disconnected.\n");
                    fflush(stdout);
                    closesocket(client);
                    break;
                } else {
                    printf("[BACKDOOR] Receive error: %lu\n", (unsigned long)GetLastError());
                    fflush(stdout);
                    closesocket(client);
                    break;
                }
            }

            closesocket(client);
            printf("[DEBUG] Client socket closed\n");
            fflush(stdout);
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
        fflush(stdout);
        closesocket(s);
        printf("[BACKDOOR] Failed to bind/listen.\n");
        fflush(stdout);
        return FALSE;
    }
}