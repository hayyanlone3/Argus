#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <thread>
#include <chrono>
#include <windows.h>
#include <winsock2.h>
#include <filesystem>
#include <random>

#pragma comment(lib, "ws2_32.lib")

#define WIN32_LEAN_AND_MEAN  // Suppress winsock warning

class HarmlessRansomwareSimulator {
private:
    std::ofstream logFile;
    std::string logPath = "ransom_sim_log.txt";
    bool running = true;
    std::mt19937 rng;  // FIXED: Proper initialization

    void log(const std::string& msg) {
        auto now = std::chrono::system_clock::now();
        auto t = std::chrono::system_clock::to_time_t(now);
        logFile << "[" << std::ctime(&t) << "] " << msg << std::endl;
        std::cout << "[RANSOM] " << msg << std::endl;
    }

    std::string encryptFake(const std::string& data) {
        std::string enc = data;
        for (char& c : enc) c ^= 0xAA;
        return enc;
    }

    void massFileEnumerationAndFakeEncryption() {
        while (running) {
            log("RANSOM: Enumerating user directories for encryption...");
            std::vector<std::string> targets = {"C:\\Users\\", "C:\\Documents\\", "C:\\Users\\Public\\"};
            
            for (const auto& dir : targets) {
                try {
                    for (const auto& entry : std::filesystem::directory_iterator(dir)) {
                        if (!running) break;
                        if (entry.is_regular_file() && entry.path().extension() != ".enc") {
                            std::string fname = entry.path().filename().string();
                            log("ENCRYPTING: " + fname + " -> " + fname + ".enc");
                        }
                    }
                } catch (...) {}
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
        }
    }

    void fakeShadowCopyDeletion() {
        while (running) {
            log("RANSOM: Deleting Volume Shadow Copies (vssadmin delete shadows)");
            log("RANSOM: Disabling Windows Defender");
            std::this_thread::sleep_for(std::chrono::seconds(5));
        }
    }

    void bitcoinRansomNoteDropper() {
        while (running) {
            std::string note = "\n*** YOUR FILES ENCRYPTED ***\nSend 5 BTC to: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh\nFILES: " + 
                               std::to_string(rng() % 100000) + "\n";
            
            // Drop fake ransom note
            std::ofstream noteFile("C:\\Users\\Public\\Desktop\\DECRYPT.html");
            noteFile << note;
            noteFile.close();
            log("DROPPED RANSOM NOTE: C:\\Users\\Public\\Desktop\\DECRYPT.html");
            std::this_thread::sleep_for(std::chrono::seconds(15));
        }
    }

    void networkPropagation() {
        while (running) {
            log("PROPAGATION: SMB EternalBlue scan 192.168.1.0/24");
            log("PROPAGATION: 5 hosts infected via MS17-010");
            
            // Fake SMB (localhost only)
            SOCKET s = socket(AF_INET, SOCK_STREAM, 0);
            sockaddr_in target = {0};
            target.sin_family = AF_INET;
            target.sin_port = htons(445);
            target.sin_addr.s_addr = inet_addr("127.0.0.1");
            connect(s, (sockaddr*)&target, sizeof(target));
            closesocket(s);
            
            std::this_thread::sleep_for(std::chrono::seconds(3));
        }
    }

    void keyloggerSimulation() {
        while (running) {
            log("KEYLOGGER: admin@domain.com:Password123!");
            std::this_thread::sleep_for(std::chrono::milliseconds(800));
        }
    }

public:
    HarmlessRansomwareSimulator() : rng(std::random_device{}()) {  // FIXED: Constructor init
        logFile.open(logPath);
        log("=== HARMLESS RANSOMWARE SIMULATOR v3.0 ===");
        log("Press ENTER to stop");
    }

    ~HarmlessRansomwareSimulator() {
        running = false;
        logFile.close();
    }

    void startRansomwareAttack() {
        std::thread encrypt(&HarmlessRansomwareSimulator::massFileEnumerationAndFakeEncryption, this);
        std::thread shadow(&HarmlessRansomwareSimulator::fakeShadowCopyDeletion, this);
        std::thread notes(&HarmlessRansomwareSimulator::bitcoinRansomNoteDropper, this);
        std::thread propagate(&HarmlessRansomwareSimulator::networkPropagation, this);
        std::thread keylog(&HarmlessRansomwareSimulator::keyloggerSimulation, this);

        std::string input;
        std::getline(std::cin, input);

        running = false;
        encrypt.join(); shadow.join(); notes.join(); propagate.join(); keylog.join();
    }
};

int main() {
    SetConsoleTitleA("svchost.exe");
    ShowWindow(GetConsoleWindow(), SW_MINIMIZE);
    Sleep(1500);
    ShowWindow(GetConsoleWindow(), SW_SHOW);

    HarmlessRansomwareSimulator ransom;
    ransom.startRansomwareAttack();
    return 0;
}