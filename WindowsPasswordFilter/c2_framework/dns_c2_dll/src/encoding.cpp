#include "encoding.h"

std::string xorEncrypt(const std::string& data, const std::string& key)
{
    std::string output = data;

    for (size_t i = 0; i < data.size(); i++) {
        output[i] = data[i] ^ key[i % key.size()];
    }

    return output;
}

std::vector<std::string> chunkData(const std::string& data, size_t chunkSize)
{
    std::vector<std::string> chunks;

    for (size_t i = 0; i < data.size(); i += chunkSize) {
        chunks.push_back(data.substr(i, chunkSize));
    }

    return chunks;
}

std::string makeDomainChunk(const std::string& chunk, const std::string& baseDomain)
{
    return chunk + "." + baseDomain;
}