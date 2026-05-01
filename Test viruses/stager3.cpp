// stager3.cpp - DLL Hijacking + Fake Ransomware (FULLY FIXED)
#include <windows.h>
#include <stdio.h>      // FILE, fopen, fwrite, fclose, fprintf
#include <string.h>     // strlen, strcpy_s, strcat_s

int WINAPI WinMain(HINSTANCE h, HINSTANCE, LPSTR, int) {
    // Stage 4: Drop fake malicious DLL
    char dllPath[MAX_PATH];
    GetTempPathA(MAX_PATH, dllPath);
    strncat(dllPath, "version.dll", MAX_PATH - strlen(dllPath) - 1);
    
    // Fake ransomware note
    char ransomNote[] = "[PENTEST RANSOMWARE SIM]\n"
                        "Your files encrypted!\n"
                        "Pay 1 BTC to 1FakeAddress\n"
                        "Files: *.docx *.pdf *.jpg\n"
                        "Decryptor: version.dll\n"
                        "TEST ONLY - HARML ESS";
    
    FILE* fp = fopen(dllPath, "wb");
    if (fp) {
        fwrite(ransomNote, 1, strlen(ransomNote), fp);
        fclose(fp);
    }
    
    // Load DLL (harmless - triggers DLL loading detection)
    HMODULE hDll = LoadLibraryA(dllPath);
    
    // Enumerate desktop files (behavioral trigger)
    WIN32_FIND_DATAA fd;
    char searchPath[MAX_PATH] = "C:\\Users\\*\\Desktop\\*.*";
    HANDLE hFind = FindFirstFileA(searchPath, &fd);
    if (hFind != INVALID_HANDLE_VALUE) {
        FindClose(hFind);
    }
    
    // Fake encryption simulation
    char encryptLog[MAX_PATH];
    strncpy(encryptLog, dllPath, MAX_PATH);
    strncat(encryptLog, ".log", MAX_PATH - strlen(encryptLog) - 1);
    
    FILE* log = fopen(encryptLog, "w");
    if (log) {
        fprintf(log, "ENCRYPTED: 0 files (pentest)\n"
                   "RANSIM COMPLETE\n"
                   "DLL: %s\n", dllPath);
        fclose(log);
    }
    
    // Notification (no sprintf_s)
    char msg[1024] = "STAGE4: DLL dropped!\n\n";
    strncat(msg, dllPath, 512);
    strncat(msg, "\n\n", 1024);
    strncat(msg, encryptLog, 1024);
    strncat(msg, "\n\nHarmless pentest!", 1024);
    
    MessageBoxA(NULL, msg, "Ransomware Simulator", MB_OK | MB_ICONERROR);
    
    // Cleanup after 10 sec
    Sleep(10000);
    DeleteFileA(dllPath);
    DeleteFileA(encryptLog);
    if (hDll) FreeLibrary(hDll);
    
    // Self-delete
    char selfPath[MAX_PATH];
    GetModuleFileNameA(NULL, selfPath, MAX_PATH);
    Sleep(1000);
    DeleteFileA(selfPath);
    
    return 0;
}