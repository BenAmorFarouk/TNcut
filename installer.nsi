!include "MUI2.nsh"

; General
Name "TNcut"
OutFile "TNcut_Setup_1.0.1.exe"
InstallDir "$PROGRAMFILES\TNcut"
InstallDirRegKey HKLM "Software\TNcut" "InstallDir"
RequestExecutionLevel admin

; Version info
VIProductVersion "1.0.1.0"
VIAddVersionKey "ProductName" "TNcut"
VIAddVersionKey "ProductVersion" "1.0.1"
VIAddVersionKey "FileDescription" "TNcut Network Monitor Installer"
VIAddVersionKey "LegalCopyright" "MIT License"

; Interface settings
!define MUI_ICON "logo.ico"
!define MUI_UNICON "logo.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "Welcome to TNcut Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will install TNcut 1.0.1 on your computer.$\r$\n$\r$\nTNcut is a network monitoring and per-device bandwidth control tool.$\r$\n$\r$\nNote: This application requires Administrator privileges and Npcap to function properly.$\r$\n$\r$\nClick Next to continue."
!define MUI_FINISHPAGE_RUN "$INSTDIR\TNCut.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch TNcut (as Administrator)"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Language
!insertmacro MUI_LANGUAGE "English"

; Installer section
Section "Install"
    SetOutPath "$INSTDIR"

    ; Copy all files from dist. Exclude the runtime database: it is created
    ; on first launch, and bundling it both locks the build against a running
    ; instance and ships the builder's scanned network data to end users.
    File /r /x "tncut.db" /x "*.db-journal" /x "*.log" "dist\TNCut\*.*"

    ; Write registry keys
    WriteRegStr HKLM "Software\TNcut" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TNcut" "DisplayName" "TNcut"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TNcut" "DisplayVersion" "1.0.1"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TNcut" "Publisher" "BenAmorFarouk"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TNcut" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TNcut" "DisplayIcon" "$INSTDIR\TNCut.exe"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TNcut" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TNcut" "NoRepair" 1

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"

    ; Create Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\TNcut"
    CreateShortcut "$SMPROGRAMS\TNcut\TNcut.lnk" "$INSTDIR\TNCut.exe" "" "$INSTDIR\TNCut.exe" 0
    CreateShortcut "$SMPROGRAMS\TNcut\Uninstall.lnk" "$INSTDIR\uninstall.exe"

    ; Create Desktop shortcut
    CreateShortcut "$DESKTOP\TNcut.lnk" "$INSTDIR\TNCut.exe" "" "$INSTDIR\TNCut.exe" 0
SectionEnd

; Uninstaller section
Section "Uninstall"
    ; Remove files
    RMDir /r "$INSTDIR"

    ; Remove shortcuts
    Delete "$DESKTOP\TNcut.lnk"
    RMDir /r "$SMPROGRAMS\TNcut"

    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\TNcut"
    DeleteRegKey HKLM "Software\TNcut"
SectionEnd
