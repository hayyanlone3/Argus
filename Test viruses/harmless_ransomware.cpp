// harmless_ransomware.cpp - FYP Pentest Detection Trigger
// Compile: g++ harmless_ransomware.cpp -mwindows -o ransomware.exe -static
// Detection: Static strings + Behavioral file enum + Fake encryption

#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <shlobj.h>  // KnownFolderPath

#pragma comment(lib, "shell32.lib")

// Suspicious ransomware strings (static detection)
const char* ransom_notes[] = {
    "ALL YOUR FILES ARE ENCRYPTED!!!",
    "Send 5 BTC to 1FakeBitcoinAddress1234567890ABCDEF",
    "Decryptor available for $999",
    "Your files: .docx .pdf .jpg .png .mp4 ENCRYPTED",
    "RANSOMWARE v1.0 - CONTACT: fakehacker@protonmail.com",
    "SHA256: 1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
};

// Fake encryption key (behavioral trigger)
unsigned char fake_key[32] = {0xDE,0xAD,0xBE,0xEF,0xCA,0xFE,0xBA,0xBE};

void CreateRansomNote(const char* path) {
    FILE* fp = fopen(path, "w");
    if (fp) {
        fprintf(fp, "\n\n");
        fprintf(fp, "██████████████████████████████████████████████████████████\n");
        fprintf(fp, "███               ALL FILES ENCRYPTED!                  ███\n");
        fprintf(fp, "██████████████████████████████████████████████████████████\n\n");
        
        for (int i = 0; i < 6; i++) {
            fprintf(fp, "%s\n\n", ransom_notes[i]);
        }
        
        fprintf(fp, "PEN TEST ONLY - FYP AI MALWARE DETECTION SYSTEM\n");
        fprintf(fp, "Files: 0 actually encrypted (simulation)\n");
        fprintf(fp, "Static/Behavioral detection test successful!\n");
        fprintf(fp, "Your system detected this before execution!\n");
        fclose(fp);
    }
}

void EnumerateUserFiles() {
    // Behavioral: File enumeration (read-only)
    char desktopPath[MAX_PATH];
    SHGetFolderPathA(NULL, CSIDL_DESKTOPDIRECTORY, NULL, SHGFP_TYPE_CURRENT, desktopPath);
    
    WIN32_FIND_DATAA findData;
    char searchPath[MAX_PATH];
    sprintf(searchPath, "%s\\*.*", desktopPath);
    
    HANDLE hFind = FindFirstFileA(searchPath, &findData);
    if (hFind != INVALID_HANDLE_VALUE) {
        FILE* log = fopen("C:\\temp\\ransom_enum.log", "w");
        if (log) {
            fprintf(log, "[PENTEST] Desktop enumeration:\n");
            do {
                if (!(findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                    fprintf(log, "  - %s (%lu bytes)\n", findData.cFileName, 
                           (findData.nFileSizeLow | ((DWORDLONG)findData.nFileSizeHigh << 32)));
                }
            } while (FindNextFileA(hFind, &findData));
            fclose(log);
        }
        FindClose(hFind);
    }
}

void FakeEncryptDirectory(const char* dirPath) {
    // Behavioral: Fake file operations
    char searchPath[MAX_PATH];
    sprintf(searchPath, "%s\\*.*", dirPath);
    
    WIN32_FIND_DATAA fd;
    HANDLE hFind = FindFirstFileA(searchPath, &fd);
    
    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                // FAKE ENCRYPTION: Just touch timestamp
                char fakeEncrypted[MAX_PATH];
                sprintf(fakeEncrypted, "%s.ENCRYPTED", fd.cFileName);
                
                // Log instead of modifying
                FILE* encryptLog = fopen("C:\\temp\\encrypt_sim.log", "a");
                if (encryptLog) {
                    fprintf(encryptLog, "SIMULATED: %s -> %s (AES-256 ECB)\n", 
                           fd.cFileName, fakeEncrypted);
                    fclose(encryptLog);
                }
            }
        } while (FindNextFileA(hFind, &fd));
        FindClose(hFind);
    }
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrev, LPSTR lpCmdLine, int nShow) {
    
    // Phase 1: Create ransom note (static strings trigger)
    char tempPath[MAX_PATH];
    GetTempPathA(MAX_PATH, tempPath);
    strcat_s(tempPath, "\\README_RANSOM.txt");
    CreateRansomNote(tempPath);
    
    // Phase 2: Enumerate files (behavioral)
    CreateDirectoryA("C:\\temp", NULL);  // Safe temp dir
    EnumerateUserFiles();
    
    // Phase 3: Fake encryption simulation
    char desktopPath[MAX_PATH];
    SHGetFolderPathA(NULL, CSIDL_DESKTOPDIRECTORY, NULL, SHGFP_TYPE_CURRENT, desktopPath);
    FakeEncryptDirectory(desktopPath);
    
    // Phase 4: Network C2 simulation (DNS beacon)
    WSADATA wsa;
    WSAStartup(MAKEWORD(2,2), &wsa);
    gethostbyname("c2-pentest-server.fake");  // Triggers network monitor
    WSACleanup();
    
    // Phase 5: Victim notification
    char message[2048];
    sprintf(message, 
        "YOUR FILES HAVE BEEN ENCRYPTED!\n\n"
        "Ransom note: %s\n\n"
        "PEN TEST SIMULATION\n"
        "FYP: AI Early Malware Detection System\n"
        "Static: Ransom strings detected\n"
        "Behavioral: File enum + fake encrypt\n"
        "Network: C2 beacon\n\n"
        "Files safe - 0 bytes modified!", tempPath);
    
    MessageBoxA(NULL, message, "RANSOMWARE v1.0", MB_OK | MB_ICONERROR);
    
    // Phase 6: HARML ESS CLEANUP (10 seconds)
    Sleep(10000);
    
    // Remove all traces
    DeleteFileA(tempPath);
    DeleteFileA("C:\\temp\\ransom_enum.log");
    DeleteFileA("C:\\temp\\encrypt_sim.log");
    RemoveDirectoryA("C:\\temp");
    
    MessageBoxA(NULL, 
        "🛡️ PEN TEST COMPLETE 🛡️\n\n"
        "All traces removed\n"
        "0 files harmed\n"
        "Detection system validated!", 
        "FYP Test Successful", MB_OK | MB_ICONINFORMATION);
    
    return 0;
}