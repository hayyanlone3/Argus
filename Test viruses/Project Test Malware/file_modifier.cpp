#include <windows.h>
#include <stdio.h>

#define TEST_FILE "C:\\fyp_test\\victim.txt"
#define RANSOM_FILE "C:\\fyp_test\\victim.txt.locked"
#define RANSOM_NOTE "[RANSOMWARE] Your file encrypted! Send 1 BTC to 1FakeWallet or lose data forever."

void setup_victim_file() {
    CreateDirectoryA("C:\\fyp_test\\", NULL);
    FILE* f = fopen(TEST_FILE, "w");
    fprintf(f, "ARGUS FYP Test File\nThis is dummy content to simulate real document\nImportant project data here...\n");
    fclose(f);
}

void inject_keystrokes(HWND notepad_hwnd) {
    // Simulate encryption keystrokes (Ctrl+A, Ctrl+H replace, type dummy data)
    SetForegroundWindow(notepad_hwnd);
    Sleep(800);
    
    // Ctrl+A (select all)
    keybd_event(VK_CONTROL, 0, 0, 0);
    keybd_event('A', 0, 0, 0);
    keybd_event('A', 0, KEYEVENTF_KEYUP, 0);
    keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0);
    Sleep(100);
    
    // Type "encrypted_" prefix
    const char* encrypt = "encrypted_dummy_data_1234567890_";
    for (int i = 0; encrypt[i]; i++) {
        keybd_event(encrypt[i], 0, 0, 0);
        keybd_event(encrypt[i], 0, KEYEVENTF_KEYUP, 0);
        Sleep(20);
    }
    Sleep(100);
}

void ransomware_operations() {
    // 1. ShellExecute victim file
    ShellExecuteA(NULL, "open", TEST_FILE, NULL, NULL, SW_SHOW);
    Sleep(2000);  // Notepad launch
    
    // 2. Inject keystrokes
    HWND notepad_hwnd = FindWindowA("Notepad", NULL);
    if (notepad_hwnd) {
        inject_keystrokes(notepad_hwnd);
        
        // 3. Ctrl+S (overwrite)
        Sleep(500);
        keybd_event(VK_CONTROL, 0, 0, 0);
        keybd_event('S', 0, 0, 0);
        keybd_event('S', 0, KEYEVENTF_KEYUP, 0);
        keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0);
        Sleep(800);  // Dialog confirm
        
        // Enter to save
        keybd_event(VK_RETURN, 0, 0, 0);
        keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0);
    }
    
    // 4. Rename to .locked
    Sleep(500);
    MoveFileA(TEST_FILE, RANSOM_FILE);
    
    // 5. Ransom note
    FILE* note = fopen("C:\\fyp_test\\READ_ME.txt", "w");
    fprintf(note, "%s\nDecrypt key: ARGUS_FYP_TEST\n", RANSOM_NOTE);
    fclose(note);
    
    // 6. Kill notepad
    system("taskkill /f /im notepad.exe >nul 2>&1");
}

void cleanup() {
    Sleep(4000);  // Observe
    char self[260]; GetModuleFileNameA(NULL, self, 260);
    DeleteFileA(self);
    DeleteFileA(RANSOM_FILE);
    DeleteFileA("C:\\fyp_test\\READ_ME.txt");
    RemoveDirectoryA("C:\\fyp_test\\");
    ExitProcess(0);
}

int WINAPI WinMain(HINSTANCE h, HINSTANCE h2, LPSTR lp, int n) {
    setup_victim_file();
    ransomware_operations();
    
    MessageBoxA(NULL, RANSOM_NOTE, "FILE ENCRYPTED - ARGUS TEST", MB_OK | MB_ICONWARNING);
    cleanup();
    return 0;
}