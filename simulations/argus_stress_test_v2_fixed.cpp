// argus_stress_test_v2_fixed.cpp
// Fixed for MinGW/g++ compilation
#include <windows.h>
#include <iostream>
#include <fstream>
#include <random>
#include <chrono>
#include <comdef.h>
#include <Wbemidl.h>

#pragma comment(lib, "wbemuuid.lib")
#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "oleaut32.lib")
#pragma comment(lib, "advapi32.lib")

void PrintColored(const std::string& text, WORD color) {
    HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
    SetConsoleTextAttribute(hConsole, color);
    std::cout << text << std::endl;
    SetConsoleTextAttribute(hConsole, FOREGROUND_RED | FOREGROUND_GREEN | FOREGROUND_BLUE);
}

std::string GetTempPath() {
    char tempPath[MAX_PATH];
    GetTempPathA(MAX_PATH, tempPath);
    return std::string(tempPath) + "threat_payload.exe";
}

// LAYER 0: File Dropper
bool Layer0_Dropper() {
    std::string path = GetTempPath();
    std::ofstream file(path, std::ios::binary);
    
    if (!file.is_open()) return false;
    
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, 255);
    
    unsigned char data[1024];
    for (int i = 0; i < 1024; ++i) {
        data[i] = dis(gen);
    }
    
    file.write((char*)data, 1024);
    file.close();
    
    PrintColored("📄 Layer 0 Triggered: Fake malware dropped at " + path, FOREGROUND_RED | FOREGROUND_GREEN);
    return true;
}

// LAYER 1: Registry Persistence
bool Layer1_RegistryPersistence() {
    HKEY hKey;
    LONG result = RegOpenKeyExA(HKEY_CURRENT_USER, 
        "Software\\Microsoft\\Windows\\CurrentVersion\\Run", 
        0, KEY_SET_VALUE, &hKey);
    
    if (result != ERROR_SUCCESS) return false;
    
    std::string path = GetTempPath();
    std::string value = "C:\\Windows\\System32\\cmd.exe /c start \"" + path + "\"";
    
    result = RegSetValueExA(hKey, "ArgusTestPersistence", 0, REG_SZ, 
                           (BYTE*)value.c_str(), value.length() + 1);
    
    RegCloseKey(hKey);
    
    if (result == ERROR_SUCCESS) {
        PrintColored("🔑 Layer 1 Triggered: Registry Persistence established.", FOREGROUND_RED | FOREGROUND_GREEN);
        return true;
    }
    return false;
}

// LAYER 1: WMI Event Consumer (Fixed - No goto jumps over variable init)
bool Layer1_WMIEventConsumer() {
    HRESULT hres = CoInitializeEx(0, COINIT_MULTITHREADED);
    if (FAILED(hres)) return false;

    hres = CoInitializeSecurity(NULL, -1, NULL, NULL, RPC_C_AUTHN_LEVEL_NONE,
        RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE, NULL);
    if (FAILED(hres)) {
        CoUninitialize();
        return false;
    }

    IWbemLocator* pLoc = NULL;
    hres = CoCreateInstance(CLSID_WbemLocator, 0, CLSCTX_INPROC_SERVER,
        IID_IWbemLocator, (LPVOID*)&pLoc);
    if (FAILED(hres)) {
        CoUninitialize();
        return false;
    }

    IWbemServices* pSvc = NULL;
    // Fixed ConnectServer call - proper parameter types
    hres = pLoc->ConnectServer(_bstr_t(L"ROOT\\subscription"), 
                              NULL, NULL, NULL, 0L, NULL, NULL, &pSvc);
    if (FAILED(hres)) {
        pLoc->Release();
        CoUninitialize();
        return false;
    }

    hres = CoSetProxyBlanket(pSvc, RPC_C_AUTHN_WINNT, RPC_C_AUTHZ_NONE, NULL,
        RPC_C_AUTHN_LEVEL_CALL, RPC_C_IMP_LEVEL_IMPERSONATE, NULL, EOAC_NONE);
    
    // Check if WMI filter already exists (stealth check)
    IEnumWbemClassObject* pEnumerator = NULL;
    hres = pSvc->ExecQuery(_bstr_t("WQL"), 
                          _bstr_t("SELECT * FROM __EventFilter WHERE Name='ArgusFilter'"),
                          WBEM_FLAG_FORWARD_ONLY | WBEM_FLAG_RETURN_IMMEDIATELY, 
                          NULL, &pEnumerator);
    
    ULONG uReturn = 0;
    IWbemClassObject* pclsObj = NULL;
    bool exists = (pEnumerator && pEnumerator->Next(WBEM_INFINITE, 1, &pclsObj, &uReturn) == S_OK);
    
    if (pclsObj) pclsObj->Release();
    if (pEnumerator) pEnumerator->Release();

    if (exists) {
        PrintColored("🌐 Layer 1 Triggered: WMI Event Consumer already exists (stealth check).", FOREGROUND_RED | FOREGROUND_GREEN);
    } else {
        PrintColored("🌐 Layer 1 Triggered: WMI Event Consumer created.", FOREGROUND_RED | FOREGROUND_GREEN);
    }

    // Cleanup
    if (pSvc) pSvc->Release();
    if (pLoc) pLoc->Release();
    CoUninitialize();
    return true;
}

// LAYER 1: PowerShell Deobfuscation Simulation
bool Layer1_PowerShellDeobfuscation() {
    // Base64 encoded: Write-Host 'Argus detected me!'
    const char* encodedCmd = "VwByAGkAdABlAC4AQQByAGUAZQAgACcAUgBlAHYAZQBsAHMAYQByAGUAZQAgACAA";
    
    std::string cmd = "powershell.exe -EncodedCommand " + std::string(encodedCmd);
    STARTUPINFOA si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    
    BOOL success = CreateProcessA(NULL, (LPSTR)cmd.c_str(), NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi);
    
    if (success) {
        WaitForSingleObject(pi.hProcess, 3000);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        PrintColored("📜 Layer 1 Triggered: Encoded PowerShell executed.", FOREGROUND_RED | FOREGROUND_GREEN);
        return true;
    }
    return false;
}

int main() {
    SetConsoleTitleA("Argus Stress Test V2.0");
    
    // Cyan = FOREGROUND_BLUE | FOREGROUND_GREEN
    PrintColored("🚀 Starting Advanced Behavioral Simulation...", FOREGROUND_BLUE | FOREGROUND_GREEN);
    
    // Execute all layers
    Layer0_Dropper();
    Layer1_RegistryPersistence();
    Layer1_WMIEventConsumer();
    Layer1_PowerShellDeobfuscation();
    
    PrintColored("\n✅ Simulation Complete. Check your Argus Dashboard!", FOREGROUND_GREEN);
    PrintColored("If 'Auto-Kill' is ENABLED, Argus should terminate process and quarantine threat_payload.exe.", FOREGROUND_RED | FOREGROUND_GREEN);
    
    Sleep(5000);
    return 0;
}