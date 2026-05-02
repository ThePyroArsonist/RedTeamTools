#define WIN32_NO_STATUS
#define SECURITY_WIN32
#define WIN32_LEAN_AND_MEAN
#define _WINSOCKAPI_ // prevent winsock.h inclusion
#include <windows.h>
#undef WIN32_NO_STATUS

#include <ntstatus.h>
#include <ntsecapi.h>
#include <sspi.h>
#include <ntsecpkg.h>

#include "../common/Logger.h"

extern "C" __declspec(dllexport)
NTSTATUS SpInitialize(
    ULONG_PTR PackageId,
    PSECPKG_PARAMETERS Parameters,
    PLSA_SECPKG_FUNCTION_TABLE FunctionTable
)
{
    LogEvent("[SSP] SpInitialize called");
    return STATUS_SUCCESS;
}

extern "C" __declspec(dllexport)
NTSTATUS SpShutdown(void)
{
    LogEvent("[SSP] SpShutdown called");
    return STATUS_SUCCESS;
}