Race Condition Handling: 
The ExecuteExploitLogic() function simulates the timing window where the wdf filter handler (wdfEvtCreate) is loaded but before secdrv completes initialization.

Persistence: 
The code uses RegSetValueEx to add a startup service entry, a classic post-exploitation technique.

Backdoor: 
A raw socket() listener is configured to listen for incoming connections, ready for a recv/send loop.

Modularity: 
This structure allows you to swap out cmd.exe for powershell or inject different payloads into the DLL loading phase easily.

How to compile:
make clean && make

Run:
./BlueRed.exe