#pragma once
#include <vector>
#include <string>

std::string xorEncrypt(const std::string& data, const std::string& key);
std::vector<std::string> chunkData(const std::string& data, size_t chunkSize = 50);
std::string makeDomainChunk(const std::string& chunk, const std::string& baseDomain);