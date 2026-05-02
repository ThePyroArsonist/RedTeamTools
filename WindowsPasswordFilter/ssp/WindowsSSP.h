#pragma once
#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_ // prevent winsock.h inclusion
#include <windows.h>
#include <ntsecapi.h>
#include <ntsecpkg.h>

extern "C" {

NTSTATUS SpInitialize(
    ULONG_PTR PackageId,
    PSECPKG_PARAMETERS Parameters,
    PLSA_SECPKG_FUNCTION_TABLE FunctionTable
);

NTSTATUS SpShutdown(void);

}