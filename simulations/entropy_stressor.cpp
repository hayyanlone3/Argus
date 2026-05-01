#include <windows.h>
#include <stdio.h>
#include <string.h>

#pragma comment(lib, "advapi32.lib")

#define DUMMY_DIR "C:\\fyp_test\\"
#define MAX_FILES 30
#define BUFFER_SIZE 4096

void cleanup() {
    Sleep(2000);
    char self_path[260]; GetModuleFileNameA(NULL, self_path, 260); DeleteFileA(self_path);
    RemoveDirectoryA(DUMMY_DIR); ExitProcess(0);
}

int WINAPI WinMain(HINSTANCE h, HINSTANCE h2, LPSTR lp, int n) {
    CreateDirectoryA(DUMMY_DIR, NULL);
    
    // Create dummy files + high-entropy "encryption" (random bytes)
    for (int i = 0; i < MAX_FILES; i++) {
        char path[260]; sprintf(path, DUMMY_DIR "dummy%d.txt", i);
        FILE* f = fopen(path, "wb"); 
        BYTE entropy[BUFFER_SIZE]; 
        for (int j = 0; j < BUFFER_SIZE; j++) entropy[j] = (BYTE)(i * j + 0xAA);  // High Shannon entropy
        fwrite(entropy, 1, BUFFER_SIZE, f); fclose(f);
        
        // Simulate rename (MODIFIED_FILE/RENAMED_FILE edges)
        char enc_path[260]; sprintf(enc_path, DUMMY_DIR "dummy%d.enc", i);
        MoveFileA(path, enc_path);
    }
    
    cleanup();
    return 0;
}