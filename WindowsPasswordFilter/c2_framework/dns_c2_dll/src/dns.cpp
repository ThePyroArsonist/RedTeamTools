#include "dns.h"
#include <winsock2.h>
#include <cstdlib>

std::vector<uint8_t> buildDnsQuery(const std::string& domain)
{
    std::vector<uint8_t> packet;

    DNS_HEADER header{};
    header.id = htons(static_cast<uint16_t>(rand() % 65535));
    header.flags = htons(0x0100);
    header.qdcount = htons(1);

    packet.insert(packet.end(),
        reinterpret_cast<uint8_t*>(&header),
        reinterpret_cast<uint8_t*>(&header) + sizeof(header));

    size_t start = 0;
    size_t end;

    while ((end = domain.find('.', start)) != std::string::npos)
    {
        uint8_t len = static_cast<uint8_t>(end - start);
        packet.push_back(len);

        packet.insert(packet.end(),
            domain.begin() + start,
            domain.begin() + end);

        start = end + 1;
    }

    uint8_t len = static_cast<uint8_t>(domain.size() - start);
    packet.push_back(len);

    packet.insert(packet.end(),
        domain.begin() + start,
        domain.end());

    packet.push_back(0x00);

    // QTYPE A
    packet.push_back(0x00);
    packet.push_back(0x01);

    // QCLASS IN
    packet.push_back(0x00);
    packet.push_back(0x01);

    return packet;
}