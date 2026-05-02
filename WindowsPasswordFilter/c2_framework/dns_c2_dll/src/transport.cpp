#include "transport.h"
#include <winsock2.h>
#include <ws2tcpip.h>

bool sendDnsQueryRaw(const std::vector<uint8_t>& packet,
                     const char* dnsServer,
                     uint16_t port)
{
    SOCKET sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == INVALID_SOCKET)
        return false;

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);

    if (inet_pton(AF_INET, dnsServer, &addr.sin_addr) <= 0) {
        closesocket(sock);
        return false;
    }

    int sent = sendto(sock,
        reinterpret_cast<const char*>(packet.data()),
        static_cast<int>(packet.size()),
        0,
        (sockaddr*)&addr,
        sizeof(addr));

    closesocket(sock);
    return sent != SOCKET_ERROR;
}