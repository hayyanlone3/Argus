#include <windows.h>
#include <stdio.h>

#define WMI_EVENT "SELECT * FROM __InstanceCreationEvent WITHIN 3600 WHERE TargetInstance ISA 'Win32_Process'"

void simulate_wmi_subscription() {
    // Simulate WMI subscription creation (triggers WMI events for Day 7+ ML)
    char wmi_cmd[512]; sprintf(wmi_cmd, "powershell.exe -c \"Get-WmiObject -Query '%s'\"", WMI_EVENT);
    STARTUPINFOA si = {0}; PROCESS_INFORMATION pi;
    CreateProcessA(NULL, wmi_cmd, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi);
    WaitForSingleObject(pi.hProcess, 2000);
}

void cleanup() {
    Sleep(5000); char self[260]; GetModuleFileNameA(NULL, self, 260); DeleteFileA(self); ExitProcess(0);
}

int WINAPI WinMain(HINSTANCE h, HINSTANCE h2, LPSTR lp, int n) {
    CreateDirectoryA("C:\\fyp_test\\", NULL);
    
    // Dormant → hourly "malicious" action simulation (3 cycles for testing)
    for (int i = 0; i < 3; i++) {
        simulate_wmi_subscription();
        Sleep(2000);  // Simulate hourly intervals (compressed for test)
    }
    
    cleanup();
    return 0;
}