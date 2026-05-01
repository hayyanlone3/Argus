#include <windows.h>
#include <winsock2.h>
#include <wininet.h>
#include <shlobj.h>
#include <stdio.h>
#include <string.h>

#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "wininet.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "user32.lib")

#define TEMP_DIR "C:\\temp\\"
#define MAX_PATH_LEN 260
#define REPLICA_NAME "harmless_replica.exe"
#define INF_NAME "autorun.inf"

void cleanup_and_exit() {
    Sleep(2000);  // Brief delay for observation
    char self_path[MAX_PATH_LEN];
    GetModuleFileNameA(NULL, self_path, MAX_PATH_LEN);
    DeleteFileA(self_path);
    
    char temp_dir[MAX_PATH_LEN];
    strcpy_s(temp_dir, TEMP_DIR);
    DeleteFileA(strcat_s(temp_dir, MAX_PATH_LEN, REPLICA_NAME));
    DeleteFileA(strcat_s(temp_dir, MAX_PATH_LEN, INF_NAME));
    RemoveDirectoryA(TEMP_DIR);
    ExitProcess(0);
}

void simulate_replication() {
    CreateDirectoryA(TEMP_DIR, NULL);
    
    char replica_path[MAX_PATH_LEN];
    strcpy_s(replica_path, MAX_PATH_LEN, TEMP_DIR);
    strcat_s(replica_path, MAX_PATH_LEN, REPLICA_NAME);
    
    char self_path[MAX_PATH_LEN];
    GetModuleFileNameA(NULL, self_path, MAX_PATH_LEN);
    CopyFileA(self_path, replica_path, FALSE);
    
    // Simulate USB autorun.inf (read-only, no write to real USB)
    char inf_path[MAX_PATH_LEN];
    strcpy_s(inf_path, MAX_PATH_LEN, TEMP_DIR);
    strcat_s(inf_path, MAX_PATH_LEN, INF_NAME);
    
    FILE* inf = fopen(inf_path, "w");
    if (inf) {
        fprintf(inf, "[AutoRun]\nopen=%s\n", REPLICA_NAME);
        fclose(inf);
        SetFileAttributesA(inf_path, FILE_ATTRIBUTE_READONLY);
    }
}

void simulate_network_enum() {
    WSADATA wsa;
    WSAStartup(MAKEWORD(2,2), &wsa);
    
    DWORD size = 16384;
    char* buffer = (char*)malloc(size);
    DWORD count = 0;
    DWORD index = 0;
    
    // Local network resources only (no outbound connections)
    WNetOpenEnumA(RESOURCE_GLOBALNET, RESOURCETYPE_ANY, 0, NULL, &index);
    while (WNetEnumResourceA(index, &count, buffer, &size) == NO_ERROR) {
        // Simulate logging (temp file, auto-cleaned)
        // Triggers behavioral detection on WNetEnumResource
    }
    
    free(buffer);
    WSACleanup();
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    // Dormant until executed; simulate behaviors
    simulate_replication();
    simulate_network_enum();
    
    // Fake infection message (windowless)
    MessageBoxA(NULL, "Harmless virus simulation for FYP - cleaning up...", "Test", MB_OK);
    
    cleanup_and_exit();
    return 0;
}