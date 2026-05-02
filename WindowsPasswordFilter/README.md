Build Steps

Step 1: Build DLLs
 - Password Filter - VS Code
Configuration: Release
Platform: x64
Type: Dynamic Library (.dll)

* OPEN VS CODE DEVELOPER CMD PROMPT *
C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Visual Studio 2022\Visual Studio Tools\VC

Compile:

PasswordFilter.cpp
Link PasswordFilter.def

Output:

PasswordFilter.dll
-  SSP - VS Code

Command to compile .dll from Developer CMD
cl /LD /EHsc PasswordFilter.cpp /I ..\common /link /OUT:PasswordFilter.dll /DEF:PasswordFilter.def


Same configuration:

Command to compile .dll
cl /LD /EHsc WindowsSSP.cpp /I ..\common /link /OUT:WindowsSSP.dll /DEF:WindowsSSP.def

Output:

TestSSP.dll
Step 2: Build Controller EXE

Compile:

controller/main.cpp

Command:
cl /EHsc main.cpp /I ..\common /link /OUT:LSA_Controller.exe netapi32.lib advapi32.lib

Output:

LSA_Controller.exe
Step 3: Deployment (Lab Only)

Copy DLLs to:

C:\Windows\System32\

Run:

LSA_Controller.exe (as Administrator)
Step 4: Reboot

Required for:

SSP loading
LSA package initialization

6. Logging Output Example
[PasswordFilter] InitializeChangeNotify called
[PasswordFilter] PasswordFilter invoked
[SSP] SpInitialize called

DNS Packet Sniffer (C / Windows Winsock)
This captures real UDP DNS packets on port 53 and logs query names.

Compile:

Windows
cl dns_sniffer.c /I "C:\Program Files\Npcap\Include" /link /LIBPATH:"C:\Program Files\Npcap\Lib" wpcap.lib ws2_32.lib

Linux:
sudo apt install libpcap-dev
gcc dns_sniffer.c -o dns_sniffer -lpcap
sudo ./dns_sniffer

Python Analyzer (Decode + Structure Logs)
This reads dns_log.txt, cleans data, and optionally decodes Base64 fragments if present.

DNS C2 DLL

Compile:
cd dns_dll

cl /EHsc /MD /I include /c src\*.cpp

link /DLL /OUT:dns_dll.dll *.obj Ws2_32.lib

Start python dashboard
python app.py