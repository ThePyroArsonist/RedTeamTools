#pragma once
#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_ // prevent winsock.h inclusion
#include <windows.h>
#include <winternl.h>

extern "C" {

BOOLEAN InitializeChangeNotify(void);

BOOLEAN PasswordFilter(
    PUNICODE_STRING AccountName,
    PUNICODE_STRING FullName,
    PUNICODE_STRING Password,
    BOOLEAN SetOperation
);

NTSTATUS PasswordChangeNotify(
    PUNICODE_STRING UserName,
    ULONG RelativeId,
    PUNICODE_STRING NewPassword
);

}