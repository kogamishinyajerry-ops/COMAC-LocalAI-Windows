; COMAC-LocalAI-Windows Inno Setup Script
; 生成专业 Windows 安装程序 (.exe) - 轻量版（CPU推理）
; 编译方式: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

#define MyAppName "COMAC-LocalAI"
#define MyAppVersion "1.0"
#define MyAppPublisher "COMAC"
#define MyAppExeName "COMAC-LocalAI.exe"
#define MyAppURL "https://github.com/comac-ai/COMAC-LocalAI-Windows"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=COMAC-LocalAI-Setup-{#MyAppVersion}-CPU
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0.17763

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 主程序 (PyInstaller 构建输出 - 单文件 exe)
Source: "dist\COMAC-LocalAI.exe"; DestDir: "{app}"; Flags: ignoreversion

; Ollama 运行时 (仅 CPU 版本)
Source: "tools\ollama\ollama.exe"; DestDir: "{app}\tools\ollama"; Flags: ignoreversion
Source: "tools\ollama\vc_redist.x64.exe"; DestDir: "{app}\tools\ollama"; Flags: ignoreversion
Source: "tools\ollama\lib\ollama\*.dll"; DestDir: "{app}\tools\ollama\lib\ollama"; Flags: ignoreversion
; 注意: CUDA 库已排除 (需要 GPU 时单独下载)

; 部署脚本
Source: "pre-deploy.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "setup.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "start.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "opencode.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "download-model.bat"; DestDir: "{app}"; Flags: ignoreversion

; 文档
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "DEPLOY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "models.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; 模板目录
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists(ExpandConstant('{src}\templates'))

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\启动 {#MyAppName}"; Filename: "{app}\start.bat"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "explorer.exe"; Parameters: "{app}"; Description: "打开安装目录"; Flags: postinstall shellexec

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\temp"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\.venv"

[Code]
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel2.Caption :=
    'COMAC 离线AI文档处理平台 v1.0' + #13#10 + #13#10 +
    '功能：文档摘要、格式转换、Excel样式优化、RAG问答、知识图谱等' + #13#10 + #13#10 +
    '本版本为 CPU 推理版本（如需 GPU 支持，请单独配置 Ollama CUDA 版）' + #13#10 + #13#10 +
    '点击"下一步"继续安装。';
end;
