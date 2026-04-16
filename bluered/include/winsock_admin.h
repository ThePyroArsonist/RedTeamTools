#pragma once

// 1. Include Winsock2 FIRST
#include <winsock2.h>
#include <ws2tcpip.h>

// 2. Include Windows
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <conio.h>

// 3. Declare Global Variables (as extern)
extern WSADATA wsaData;
extern int wsaInitResult;

// 4. Function Prototypes
extern void InitializeWinsock(void);
extern BOOL IsAdmin(void);
