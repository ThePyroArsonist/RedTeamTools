#pragma once
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// WDF Event Queue Handle (Simulated/Extended)
typedef struct _WDF_EVENT_QUEUE {
    HANDLE hEvent;
    DWORD dwQueueId;
    DWORD dwFlags;
} WDF_EVENT_QUEUE, *PWDF_EVENT_QUEUE;

// Pipe-based Startup Info
typedef struct _STARTUPINFOW_PIPE {
    DWORD dwSize;
    HANDLE hStdInput;
    HANDLE hStdOutput;
    HANDLE hStdError;
    DWORD dwFlags;
} STARTUPINFOW_PIPE, *PSTARTUPINFOW_PIPE;
