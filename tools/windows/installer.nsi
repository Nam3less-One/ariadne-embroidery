Unicode true
!include "MUI2.nsh"
!include "x64.nsh"
!include "WinVer.nsh"
!include "FileFunc.nsh"
Var NoIntegration
Name "Ariadne Embroidery Studio"
OutFile "${OUTPUT_FILE}"
InstallDir "$LOCALAPPDATA\Programs\Ariadne"
InstallDirRegKey HKCU "Software\Ariadne" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID zlib
ShowInstDetails show
ShowUninstDetails show
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey "ProductName" "Ariadne Embroidery Studio"
VIAddVersionKey "FileDescription" "Ariadne Windows x64 Setup"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "LegalCopyright" "MIT licensed. Project Ariadne contributors."
!define MUI_WELCOMEPAGE_TEXT "Install Ariadne for your Windows account.$\r$\n$\r$\nPython and required libraries are included. No paid service or account is needed.$\r$\n$\r$\nThis is an early-access embroidery drafting tool. Review and test sew every design."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\Ariadne.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Ariadne"
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "Ariadne requires 64-bit Windows."
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_ICONSTOP "Ariadne requires Windows 10 or newer."
    Abort
  ${EndIf}
  SetShellVarContext current
  ${GetParameters} $0
  ClearErrors
  ${GetOptions} $0 "/NOINTEGRATION" $1
  StrCpy $NoIntegration 0
  ${IfNot} ${Errors}
    StrCpy $NoIntegration 1
  ${EndIf}
FunctionEnd

Section "Ariadne"
  SetOutPath "$INSTDIR"
  File /r "${APP_DIR}\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteINIStr "$INSTDIR\install-mode.ini" "Ariadne" "NoIntegration" "$NoIntegration"
  ${If} $NoIntegration == 0
  WriteRegStr HKCU "Software\Ariadne" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ariadne" "DisplayName" "Ariadne Embroidery Studio"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ariadne" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ariadne" "Publisher" "Project Ariadne contributors"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ariadne" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ariadne" "DisplayIcon" "$INSTDIR\Ariadne.exe"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ariadne" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ariadne" "NoRepair" 1
  CreateDirectory "$SMPROGRAMS\Ariadne"
  CreateShortcut "$SMPROGRAMS\Ariadne\Ariadne.lnk" "$INSTDIR\Ariadne.exe"
  CreateShortcut "$SMPROGRAMS\Ariadne\Getting started.lnk" "$INSTDIR\START-HERE.txt"
  ${EndIf}
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  ReadINIStr $NoIntegration "$INSTDIR\install-mode.ini" "Ariadne" "NoIntegration"
  !include "${UNINSTALL_FILES}"
  Delete "$INSTDIR\install-mode.ini"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  ${If} $NoIntegration != 1
  Delete "$SMPROGRAMS\Ariadne\Ariadne.lnk"
  Delete "$SMPROGRAMS\Ariadne\Getting started.lnk"
  RMDir "$SMPROGRAMS\Ariadne"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ariadne"
  DeleteRegKey HKCU "Software\Ariadne"
  ${EndIf}
SectionEnd
