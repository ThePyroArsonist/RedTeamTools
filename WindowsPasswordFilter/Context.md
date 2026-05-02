# LSA Lab Framework

## Purpose
This project simulates Windows LSA authentication extension mechanisms for defensive security research and detection engineering.

It includes:
- Password Filter DLL (event logging only)
- Security Support Provider (SSP stub)
- Registry-based LSA package registration tool
- Central controller executable

## Security Scope
This project is strictly non-malicious:
- No credential capture
- No authentication bypass
- No LSASS memory manipulation
- No persistence techniques beyond registry simulation

## Components

### Password Filter
Simulates Windows password change notification callbacks:
- InitializeChangeNotify
- PasswordFilter
- PasswordChangeNotify

### SSP Module
Simulates authentication package lifecycle:
- SpInitialize
- SpShutdown

### Controller
Registers LSA packages via:
- HKLM\System\CurrentControlSet\Control\Lsa

## Execution Flow
1. Administrator runs controller
2. Registry keys are added
3. On reboot:
   - LSASS loads SSP
   - Password filter hooks become active
4. Events are logged to C:\LSA_Lab_Log.txt

## Defensive Use Cases
- Detect LSA registry modification
- Monitor LSASS module loading
- Validate Sysmon event coverage
- Test EDR alerts for authentication extension changes

## Detection Targets
- Registry key changes in LSA hive
- Unsigned DLL loads in LSASS
- New authentication packages registered

## Lab Requirements
- Isolated domain controller
- Snapshotted VM environment
- Admin privileges for registry modifications only

## Intended Use
- Blue team detection engineering
- Red team simulation of authentication extensions (non-invasive)
- Windows internals research