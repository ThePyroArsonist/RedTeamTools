#include <windows.h>
#include <iostream>

// DLL Must be loaded before client can be used

typedef bool (*SendDnsDataFn)(
    const char* msg,
    const char* dnsServer,
    const char* baseDomain,
    unsigned short port
);

typedef bool (*SendDnsDataBidirectionalFn)(
    const char* msg,
    const char* dnsServer,
    const char* baseDomain,
    const char* key,
    unsigned short port
);

int main()
{
    // -------------------------------------------------
    // DLL is assumed already loaded by privileged host
    // -------------------------------------------------

    HMODULE dll = GetModuleHandleA("dns_dll.dll");

    if (!dll) {
        std::cout << "[ERROR] DLL not loaded in process\n";
        return 1;
    }

    // -------------------------------------------------
    // Resolve exported functions
    // -------------------------------------------------

    auto SendDnsData =
        (SendDnsDataFn)GetProcAddress(dll, "SendDnsData");

    auto SendDnsDataBidirectional =
        (SendDnsDataBidirectionalFn)GetProcAddress(dll, "SendDnsDataBidirectional");

    if (!SendDnsData || !SendDnsDataBidirectional) {
        std::cout << "[ERROR] Failed to resolve exports\n";
        return 1;
    }

    // -------------------------------------------------
    // Call functions
    // -------------------------------------------------

    SendDnsData(
        "hello lab traffic",
        "127.0.0.1",
        "lab.local",
        53
    );

    SendDnsDataBidirectional(
        "hello secure channel",
        "127.0.0.1",
        "lab.local",
        "key123",
        53
    );

    std::cout << "[OK] Calls executed\n";
}