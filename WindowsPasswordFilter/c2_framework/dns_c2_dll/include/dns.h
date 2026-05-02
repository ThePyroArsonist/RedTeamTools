#pragma once
#include <vector>
#include <string>
#include <cstdint>

#pragma pack(push, 1)
struct DNS_HEADER {
    uint16_t id;
    uint16_t flags;
    uint16_t qdcount;
    uint16_t ancount;
    uint16_t nscount;
    uint16_t arcount;
};
#pragma pack(pop)

std::vector<uint8_t> buildDnsQuery(const std::string& domain);