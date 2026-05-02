#pragma once
#include <vector>
#include <cstdint>

bool sendDnsQueryRaw(const std::vector<uint8_t>& packet,
                     const char* dnsServer,
                     uint16_t port);