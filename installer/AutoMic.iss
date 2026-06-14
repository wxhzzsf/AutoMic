; ===== AutoMic 一键安装脚本 (Inno Setup 6.1+) =====
; 编译: iscc installer\AutoMic.iss  (需先用 build.bat 生成 dist\AutoMic.exe)
; 产物: installer\Output\AutoMic-Setup.exe
;
; 安装包会:
;   1. 把 AutoMic 装到 Program Files
;   2. (可选,默认勾选) 自动从官网下载并静默安装 VB-CABLE 虚拟声卡
;   3. 创建开始菜单/桌面快捷方式, 可选开机自启
;   4. 安装完启动 AutoMic (若刚装了 VB-CABLE 则提示重启)
;
; 注意: VB-CABLE 是 VB-Audio 的捐赠制软件, 其许可不允许二次分发安装包,
;       所以这里是"运行时从官网下载", 而不是把它打包进本安装包。

#define MyAppName "AutoMic"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AutoMic"
#define MyAppURL "https://github.com/wxhzzsf/AutoMic"
#define MyAppExeName "AutoMic.exe"
#define VBCableUrl "https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack45.zip"

[Setup]
AppId={{8E3D9B7A-7C42-4E2B-9F0E-1A2B3C4D5E6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; 安装驱动需要管理员权限
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename=AutoMic-Setup
SetupIconFile=..\assets\automic.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
; 只用 Inno Setup 自带的 Default.isl(英文), 保证任意环境/CI 都能编译。
; (ChineseSimplified.isl 不在 Inno 官方发行里, 引用会导致编译失败)
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "vbcable"; Description: "Download && install VB-CABLE virtual audio driver / 下载并安装 VB-CABLE 虚拟声卡 (uncheck if already installed)"; GroupDescription: "Dependencies / 依赖:"
Name: "autostart"; Description: "Start AutoMic on login / 开机自动启动 (recommended)"; GroupDescription: "Options / 选项:"
Name: "desktopicon"; Description: "Create desktop shortcut / 创建桌面快捷方式"; GroupDescription: "Options / 选项:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\automic.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\automic.ico"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\automic.ico"; Tasks: desktopicon
Name: "{commonstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\automic.ico"; Tasks: autostart

[Run]
; 安装完成后启动 (若刚装了 VB-CABLE 需要重启, 则跳过启动)
Filename: "{app}\{#MyAppExeName}"; Description: "Run {#MyAppName} now / 立即运行"; Flags: nowait postinstall skipifsilent; Check: not RebootNeeded

[Code]
var
  DownloadPage: TDownloadWizardPage;
  RebootRequired: Boolean;

function RebootNeeded: Boolean;
begin
  Result := RebootRequired;
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(
    'Downloading VB-CABLE / 下载虚拟声卡', 'Fetching from vb-audio.com ... / 正在从官网下载, 请稍候', nil);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = wpReady) and WizardIsTaskSelected('vbcable') then
  begin
    DownloadPage.Clear;
    DownloadPage.Add('{#VBCableUrl}', 'vbcable.zip', '');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
      except
        if DownloadPage.AbortedByUser then
          Result := False
        else
        begin
          SuppressibleMsgBox(
            '下载 VB-CABLE 失败, 将跳过自动安装。' + #13#10 +
            '你可以稍后到 https://vb-audio.com/Cable/ 手动安装。' + #13#10#13#10 +
            '错误: ' + GetExceptionMessage,
            mbInformation, MB_OK, IDOK);
          Result := True;
        end;
      end;
    finally
      DownloadPage.Hide;
    end;
  end;
end;

procedure InstallVBCable;
var
  ResultCode: Integer;
  ZipPath, ExtractDir, SetupExe: String;
begin
  ZipPath := ExpandConstant('{tmp}\vbcable.zip');
  ExtractDir := ExpandConstant('{tmp}\vbcable');
  if not FileExists(ZipPath) then
    Exit;

  // 用 PowerShell 解压 (Win10/11 自带)
  if not Exec('powershell.exe',
       '-NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath ''' +
       ZipPath + ''' -DestinationPath ''' + ExtractDir + ''' -Force"',
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    SuppressibleMsgBox('解压 VB-CABLE 失败, 请稍后手动安装。', mbInformation, MB_OK, IDOK);
    Exit;
  end;

  SetupExe := ExtractDir + '\VBCABLE_Setup_x64.exe';
  if not FileExists(SetupExe) then
    SetupExe := ExtractDir + '\VBCABLE_Setup.exe';
  if not FileExists(SetupExe) then
  begin
    SuppressibleMsgBox('没找到 VB-CABLE 安装程序, 请稍后手动安装。', mbInformation, MB_OK, IDOK);
    Exit;
  end;

  // 静默安装 (-i 安装, -h 隐藏弹窗); 安装包已运行在管理员权限下
  WizardForm.StatusLabel.Caption := '正在安装 VB-CABLE 虚拟声卡...';
  if Exec(SetupExe, '-i -h', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
    RebootRequired := True
  else
    SuppressibleMsgBox('VB-CABLE 安装未成功, 请稍后手动安装。', mbInformation, MB_OK, IDOK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('vbcable') then
    InstallVBCable;
end;

function NeedRestart: Boolean;
begin
  Result := RebootRequired;
end;
