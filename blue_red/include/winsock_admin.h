#pragma once

// Include Windows headers FIRST (defines WSADATA, BOOL, HANDLE, etc.)
#include <winsock2.h>
#include <windows.h>
#include <ws2tcpip.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <conio.h>

// Global variables for Winsock initialization (Declaration)
extern WSADATA wsaData;
extern int wsaInitResult;

// Initialize Winsock function
void InitializeWinsock(void);

// Check Admin Rights
BOOL IsAdmin(void);
