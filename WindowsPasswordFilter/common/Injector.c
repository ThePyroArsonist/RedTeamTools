#define _CRT_SECURE_NO_WARNINGS
#pragma warning(disable: 6031)  // Return value ignored

#include <Windows.h>
#include <TlHelp32.h>
#include <stdio.h>
#include <string.h>

// Find process by PID
int CrawlProcess(int pid) {
	PROCESSENTRY32 pe32;
	HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);

	if (hSnapshot == INVALID_HANDLE_VALUE) {
		printf("[!] CreateToolhelp32Snapshot : Error %d\n", GetLastError());
		return -1;
	}

	pe32.dwSize = sizeof(PROCESSENTRY32);

	if (!Process32First(hSnapshot, &pe32)) {
		printf("[-] Process32First : Error %d\n", GetLastError());
		CloseHandle(hSnapshot);
		return -1;
	}

	do {
		if (pe32.th32ProcessID == pid) {
			CloseHandle(hSnapshot);
			return 0;  // Found
		}
	} while (Process32Next(hSnapshot, &pe32));

	CloseHandle(hSnapshot);
	return -1;  // Not found
}

void LoadLibraryInjection(int pid, const char* dllPath) {
	printf("\n[+] DLL Injection\n");
	printf("[+] Target PID: %d\n", pid);
	printf("[+] DLL Path: %s\n\n", dllPath);

	// Step 1: Validate DLL exists
	printf("[1] Validating DLL file...\n");
	if (GetFileAttributesA(dllPath) == INVALID_FILE_ATTRIBUTES) {
		printf("[-] DLL file not found: %s\n", dllPath);
		return;
	}

	// Step 2: Get absolute path (LoadLibrary requires absolute path)
	printf("[2] Resolving absolute path...\n");
	char absPath[MAX_PATH];
	if (!GetFullPathNameA(dllPath, MAX_PATH, absPath, NULL)) {
		printf("[-] Failed to get absolute path\n");
		return;
	}
	printf("    Absolute path: %s\n", absPath);

	// Step 3: Open target process
	printf("[3] Opening target process...\n");
	HANDLE hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, pid);
	if (hProcess == NULL) {
		printf("[-] OpenProcess failed: %d\n", GetLastError());
		return;
	}
	printf("    Process handle: 0x%p\n", hProcess);

	// Step 4: Allocate memory in target process for DLL path string
	printf("[4] Allocating memory in target process...\n");
	SIZE_T pathLen = strlen(absPath) + 1;  // +1 for null terminator
	LPVOID remoteMemory = VirtualAllocEx(
		hProcess,
		NULL,
		pathLen,
		MEM_COMMIT | MEM_RESERVE,
		PAGE_READWRITE  // Only RW needed for string data
	);

	if (remoteMemory == NULL) {
		printf("[-] VirtualAllocEx failed: %d\n", GetLastError());
		CloseHandle(hProcess);
		return;
	}
	printf("    Allocated %zu bytes at: 0x%p\n", pathLen, remoteMemory);

	// Step 5: Write DLL path string to allocated memory
	printf("[5] Writing DLL path to remote process...\n");
	SIZE_T written;
	if (!WriteProcessMemory(hProcess, remoteMemory, absPath, pathLen, &written)) {
		printf("[-] WriteProcessMemory failed: %d\n", GetLastError());
		VirtualFreeEx(hProcess, remoteMemory, 0, MEM_RELEASE);
		CloseHandle(hProcess);
		return;
	}
	printf("    Written %zu bytes\n", written);

	// Step 6: Get address of LoadLibraryA from kernel32.dll
	printf("[6] Resolving LoadLibraryA address...\n");
	HMODULE hKernel32 = GetModuleHandleA("kernel32.dll");
	if (hKernel32 == NULL) {
		printf("[-] GetModuleHandle(kernel32.dll) failed: %d\n", GetLastError());
		VirtualFreeEx(hProcess, remoteMemory, 0, MEM_RELEASE);
		CloseHandle(hProcess);
		return;
	}

	FARPROC loadLibraryAddr = GetProcAddress(hKernel32, "LoadLibraryA");
	if (loadLibraryAddr == NULL) {
		printf("[-] GetProcAddress(LoadLibraryA) failed: %d\n", GetLastError());
		VirtualFreeEx(hProcess, remoteMemory, 0, MEM_RELEASE);
		CloseHandle(hProcess);
		return;
	}
	printf("    LoadLibraryA at: 0x%p\n", loadLibraryAddr);

	// Step 7: Create remote thread to execute LoadLibraryA(dllPath)
	printf("[7] Creating remote thread...\n");
	HANDLE hThread = CreateRemoteThread(
		hProcess,
		NULL,
		0,
		(LPTHREAD_START_ROUTINE)loadLibraryAddr,  // Thread function: LoadLibraryA
		remoteMemory,                             // Thread parameter: DLL path
		0,
		NULL
	);

	if (hThread == NULL) {
		printf("[-] CreateRemoteThread failed: %d\n", GetLastError());
		VirtualFreeEx(hProcess, remoteMemory, 0, MEM_RELEASE);
		CloseHandle(hProcess);
		return;
	}

	printf("    Thread created, waiting for completion...\n");

	// Step 8: Wait for LoadLibrary to complete
	printf("[8] Waiting for DLL to load...\n");
	WaitForSingleObject(hThread, INFINITE);

	// Step 9: Check if LoadLibrary succeeded
	printf("[9] Checking injection result...\n");
	DWORD exitCode = 0;
	GetExitCodeThread(hThread, &exitCode);

	if (exitCode == 0) {
		printf("[-] LoadLibrary failed in target process\n");
	}
	else {
		printf("    Module handle: 0x%x\n", exitCode);
		printf("\n[+] DLL injection complete!\n");
		printf("[+] DLL successfully injected into PID %d\n", pid);
	}

	// Cleanup
	CloseHandle(hThread);
	VirtualFreeEx(hProcess, remoteMemory, 0, MEM_RELEASE);
	CloseHandle(hProcess);
}

int main() {
	int pid_inject;
	char dllPath[MAX_PATH];

	printf("=====================================\n");
	printf("  DLL Injector - LoadLibrary Method  \n");
	printf("=====================================\n\n");

	printf("[-] PID to inject: ");
	scanf("%d", &pid_inject);

	// Verify process exists
	if (CrawlProcess(pid_inject) != 0) {
		printf("[!] Process with PID %d not found!\n", pid_inject);
		return 1;
	}
	printf("[+] Process with PID %d found\n", pid_inject);

	printf("[-] DLL path: ");
	scanf("%s", dllPath);

	LoadLibraryInjection(pid_inject, dllPath);

	printf("\nPress Enter to exit...");
	getchar();
	getchar();

	return 0;
}