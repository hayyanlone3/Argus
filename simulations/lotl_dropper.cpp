#include <windows.h>
#include <stdio.h>

void cleanup() {
    Sleep(3000); char self[260]; GetModuleFileNameA(NULL, self, 260); DeleteFileA(self); ExitProcess(0);
}

int WINAPI WinMain(HINSTANCE h, HINSTANCE h2, LPSTR lp, int n) {
    // Stage 1: Spawn cmd → powershell (LotL chain)
    STARTUPINFOA si = {0}; PROCESS_INFORMATION pi;
    char cmd[] = "cmd.exe /c powershell.exe -c \"Add-Content -Path 'C:\\fyp_test\\script.ps1' -Value 'Write-Host \\'Harmless LotL test\\''; & 'C:\\fyp_test\\script.ps1'\"";
    CreateProcessA(NULL, cmd, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi);
    WaitForSingleObject(pi.hProcess, 5000); CloseHandle(pi.hProcess); CloseHandle(pi.hThread);
    
    // Stage 2: Simulate registry run key (read-only check, no write)
    HKEY hkey; if (RegOpenKeyExA(HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, KEY_READ, &hkey) == ERROR_SUCCESS) {
        RegCloseKey(hkey);  // Triggers registry access events
    }
    
    CreateDirectoryA("C:\\fyp_test\\", NULL);
    cleanup();
    return 0;
}