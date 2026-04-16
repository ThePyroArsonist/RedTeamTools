#pragma once

// Include winsock2.h FIRST
#include <winsock2.h>
#include <ws2tcpip.h>

// Include windows.h
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <conio.h>

// Function Declarations (Prototypes Only)
void InitializeWinsock(void);
BOOL IsAdmin(void);
