#include "../include/config.h"

BOOL StartBackdoor(void) {
    SOCKET s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in address = {0};
    int opt = 1;

    if (s == INVALID_SOCKET) {
        printf("[BACKDOOR] Failed to create socket.\n");
        return FALSE;
    }

    setsockopt(s, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(int));

    address.sin_family = AF_INET;
    
    if (inet_pton(AF_INET, BACKDOOR_HOST, &address.sin_addr) == 1) {
        address.sin_port = htons(BACKDOOR_PORT);
    } else {
        address.sin_addr.s_addr = inet_addr(BACKDOOR_HOST);
    }

    if (bind(s, (struct sockaddr*)&address, sizeof(address)) != SOCKET_ERROR) {
        if (listen(s, SOCKET_BACKLOG) != SOCKET_ERROR) {
            // Show we're listening
            char hostip[16];
            inet_ntop(AF_INET, &address.sin_addr, hostip, sizeof(hostip) - 1);
            printf("[BACKDOOR] Listener ready on %s:%d\n", hostip, BACKDOOR_PORT);
            printf("[BACKDOOR] Waiting for client...\n");
            printf("[BACKDOOR] Press Ctrl+C to stop.\n");

            // Now accept connections
            SOCKET client = accept(s, NULL, NULL);
            if (client != INVALID_SOCKET) {
                printf("[BACKDOOR] Client connected from %d\n", client);
                
                // Receive loop
                while (TRUE) {
                    int bytes = recv(client, hostip, sizeof(hostip) - 1, 0);
                    if (bytes > 0) {
                        hostip[bytes] = 0;
                        printf("[BACKDOOR] Received: %s\n", hostip);
                    } else if (bytes == 0) {
                        printf("[BACKDOOR] Client disconnected.\n");
                        closesocket(client);
                        break;
                    } else {
                        printf("[BACKDOOR] Receive error: %lu\n", GetLastError());
                        closesocket(client);
                        break;
                    }
                }

                closesocket(client);
            } else {
                printf("[BACKDOOR] Failed to accept client.\n");
            }
            closesocket(s);
            return TRUE;
        }
    }

    printf("[BACKDOOR] Failed to bind/listen.\n");
    closesocket(s);
    return FALSE;
}
