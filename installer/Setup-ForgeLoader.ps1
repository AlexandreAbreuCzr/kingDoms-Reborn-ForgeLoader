param(
    [ValidateSet('Install','Restore','Inspect')][string]$Mode='Install',
    [string]$GamePath,
    [string]$SavedPath=(Join-Path $env:LOCALAPPDATA 'PunCity\Saved'),
    [switch]$NoUI
)
$ErrorActionPreference='Stop'
function Get-BytesHash([byte[]]$Bytes) {
    $sha=[Security.Cryptography.SHA256]::Create()
    try {return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant()} finally {$sha.Dispose()}
}
function Convert-Hex([string]$Text) {
    if($Text.Length % 2 -ne 0){throw 'Invalid patch hex'}
    $bytes=New-Object byte[] ($Text.Length/2)
    for($i=0;$i -lt $bytes.Length;$i++){$bytes[$i]=[Convert]::ToByte($Text.Substring($i*2,2),16)}
    return ,$bytes
}
function Write-Atomic([string]$Path,[byte[]]$Bytes) {
    $temp=$Path+'.forgeloader-'+[guid]::NewGuid().ToString('N')
    try {
        [IO.File]::WriteAllBytes($temp,$Bytes)
        if(Test-Path -LiteralPath $Path){[IO.File]::Replace($temp,$Path,[System.Management.Automation.Language.NullString]::Value)}else{[IO.File]::Move($temp,$Path)}
    } finally {if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp}}
}
function Get-Layout([string]$Root) {
    $full=[IO.Path]::GetFullPath($Root)
    $exe=Join-Path $full 'PunCity\Binaries\Win64\PrototypeCity-Win64-Shipping.exe'
    if(!(Test-Path -LiteralPath $exe -PathType Leaf)){throw 'Escolha a pasta completa do jogo, que contem PunCity e KingdomsReborn.exe.'}
    return @{Root=$full;Exe=$exe;Dll=(Join-Path (Split-Path $exe) 'KingdomsPortraits.dll');Data=(Join-Path $full 'ForgeLoader')}
}
function Assert-GameClosed($Layout) {
    $active=@(Get-Process -ErrorAction SilentlyContinue | Where-Object {$_.Path -and $_.Path.Equals($Layout.Exe,[StringComparison]::OrdinalIgnoreCase)})
    if($active.Count){throw 'Feche o Kingdoms Reborn antes de instalar ou restaurar.'}
}
function Read-Payload {
    $patch=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'payload\player-patch.json') -Raw | ConvertFrom-Json
    $dll=[IO.File]::ReadAllBytes((Join-Path $PSScriptRoot 'payload\KingdomsPortraits.dll'))
    if($patch.schema -ne 1 -or (Get-BytesHash $dll) -ne $patch.dll_sha256){throw 'Pacote danificado: baixe e extraia o ZIP novamente.'}
    return @{Patch=$patch;Dll=$dll}
}
function Invoke-Install($Layout,[string]$Saved) {
    $payload=Read-Payload;$patch=$payload.Patch
    $raw=[IO.File]::ReadAllBytes($Layout.Exe);$current=Get-BytesHash $raw
    if($current -ne $patch.source_sha256 -and $current -ne $patch.target_sha256){throw 'Versao do jogo diferente da suportada. Nenhum arquivo foi alterado.'}
    $hadDll=Test-Path -LiteralPath $Layout.Dll
    $currentDll=if($hadDll){Get-BytesHash ([IO.File]::ReadAllBytes($Layout.Dll))}else{''}
    if($hadDll -and $currentDll -ne $patch.dll_sha256 -and @($patch.upgrade_from_dll_sha256) -notcontains $currentDll){throw 'Ja existe um runtime desconhecido. Arquivos preservados; restaure a instalacao original antes de continuar.'}
    if($current -eq $patch.target_sha256 -and $hadDll -and $currentDll -eq $patch.dll_sha256){Install-ModTools $Layout;return @{status='already-installed';message='ForgeLoader ja esta instalado. Use Instalar-Mod.cmd ou o botao Instalar mod no jogo.'}}
    Assert-GameClosed $Layout
    if($current -eq $patch.source_sha256){
        if($raw.Length -ne $patch.source_length){throw 'Tamanho original inesperado'}
        $modified=New-Object byte[] ([int]$patch.target_length)
        [Array]::Copy($raw,$modified,$raw.Length)
        foreach($change in $patch.changes){
            $before=Convert-Hex $change.before;$after=Convert-Hex $change.after;$offset=[int]$change.offset
            if($before.Length -ne $after.Length -or $offset -lt 0 -or $offset+$before.Length -gt $raw.Length){throw 'Intervalo do patch invalido'}
            for($i=0;$i -lt $before.Length;$i++){if($raw[$offset+$i] -ne $before[$i]){throw 'Cabecalho original inesperado'}}
            [Array]::Copy($after,0,$modified,$offset,$after.Length)
        }
        $append=Convert-Hex $patch.append_hex
        if($raw.Length+$append.Length -ne $modified.Length){throw 'Tamanho final do patch invalido'}
        [Array]::Copy($append,0,$modified,$raw.Length,$append.Length)
    }else{$modified=$raw}
    if((Get-BytesHash $modified) -ne $patch.target_sha256){throw 'Verificacao final do EXE falhou. Instalacao cancelada.'}
    $backup=Join-Path $Layout.Data ('Backups\'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8))
    [IO.Directory]::CreateDirectory($backup) | Out-Null
    [IO.File]::WriteAllBytes((Join-Path $backup 'game.exe'),$raw)
    if((Get-BytesHash ([IO.File]::ReadAllBytes((Join-Path $backup 'game.exe')))) -ne $current){throw 'Falha ao verificar backup'}
    if($hadDll){Copy-Item -LiteralPath $Layout.Dll -Destination (Join-Path $backup 'runtime.dll')}
    $playerInfo=Join-Path $Saved 'PlayerInfo.dat';$hadPlayer=Test-Path -LiteralPath $playerInfo
    if($hadPlayer){Copy-Item -LiteralPath $playerInfo -Destination (Join-Path $backup 'PlayerInfo.dat')}
    $record=@{schema=1;exe_sha256=$current;had_dll=[bool]$hadDll;had_player_info=[bool]$hadPlayer;backup=$backup}
    if($hadDll){$record.dll_sha256=Get-BytesHash ([IO.File]::ReadAllBytes((Join-Path $backup 'runtime.dll')))}
    if($hadPlayer){$record.player_sha256=Get-BytesHash ([IO.File]::ReadAllBytes((Join-Path $backup 'PlayerInfo.dat')))}
    $record | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $backup 'backup.json') -Encoding UTF8
    try {
        Write-Atomic $Layout.Exe $modified
        Write-Atomic $Layout.Dll $payload.Dll
        Install-ModTools $Layout
        $record | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Layout.Data 'last-install.json') -Encoding UTF8
    }catch{
        Write-Atomic $Layout.Exe $raw
        if($hadDll){Write-Atomic $Layout.Dll ([IO.File]::ReadAllBytes((Join-Path $backup 'runtime.dll')))}elseif(Test-Path -LiteralPath $Layout.Dll){Remove-Item -LiteralPath $Layout.Dll}
        throw
    }
    return @{status='installed';backup=$backup;message='Instalado! Abra o jogo e use Meus mods ou Instalar mod. Fotos ficam em Configuracoes do Lider.'}
}
function Install-ModTools($Layout) {
    [IO.Directory]::CreateDirectory((Join-Path $Layout.Root 'Mods'))|Out-Null
    [IO.Directory]::CreateDirectory($Layout.Data)|Out-Null
    foreach($name in @('Install-Mod.ps1','Instalar-Mod.cmd')){
        $source=Join-Path $PSScriptRoot $name
        if(Test-Path -LiteralPath $source){Write-Atomic (Join-Path $Layout.Data $name) ([IO.File]::ReadAllBytes($source))}
    }
}
function Invoke-Restore($Layout,[string]$Saved) {
    Assert-GameClosed $Layout
    $payload=Read-Payload;$patch=$payload.Patch
    $recordPath=Join-Path $Layout.Data 'last-install.json'
    if(!(Test-Path -LiteralPath $recordPath)){throw 'Nenhum backup deste instalador foi encontrado nesta pasta do jogo.'}
    $record=Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
    $allowed=[IO.Path]::GetFullPath((Join-Path $Layout.Data 'Backups'))+[IO.Path]::DirectorySeparatorChar
    $backup=[IO.Path]::GetFullPath($record.backup)
    if(!$backup.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase)){throw 'Caminho de backup invalido'}
    if((Get-BytesHash ([IO.File]::ReadAllBytes($Layout.Exe))) -ne $patch.target_sha256 -or !(Test-Path -LiteralPath $Layout.Dll) -or (Get-BytesHash ([IO.File]::ReadAllBytes($Layout.Dll))) -ne $patch.dll_sha256){throw 'Arquivos atuais foram alterados ou atualizados. Restauracao automatica recusada.'}
    $original=[IO.File]::ReadAllBytes((Join-Path $backup 'game.exe'))
    if((Get-BytesHash $original) -ne $record.exe_sha256){throw 'Backup do EXE danificado'}
    if($record.had_dll){$oldDll=[IO.File]::ReadAllBytes((Join-Path $backup 'runtime.dll'));if((Get-BytesHash $oldDll) -ne $record.dll_sha256){throw 'Backup de DLL danificado'}}
    if($record.had_player_info){$oldPlayer=[IO.File]::ReadAllBytes((Join-Path $backup 'PlayerInfo.dat'));if((Get-BytesHash $oldPlayer) -ne $record.player_sha256){throw 'Backup do perfil danificado'}}
    $safety=Join-Path $backup ('BeforeRestore-'+[guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($safety) | Out-Null
    Copy-Item -LiteralPath $Layout.Exe,$Layout.Dll -Destination $safety
    $playerInfo=Join-Path $Saved 'PlayerInfo.dat'
    if(Test-Path -LiteralPath $playerInfo){Copy-Item -LiteralPath $playerInfo -Destination $safety}
    Write-Atomic $Layout.Exe $original
    if($record.had_dll){Write-Atomic $Layout.Dll $oldDll}else{Remove-Item -LiteralPath $Layout.Dll}
    if($record.had_player_info){[IO.Directory]::CreateDirectory($Saved)|Out-Null;Write-Atomic $playerInfo $oldPlayer}elseif(Test-Path -LiteralPath $playerInfo){Remove-Item -LiteralPath $playerInfo}
    return @{status='restored';message='Backup anterior restaurado. Seus saves de cidades nao foram alterados.'}
}
if($MyInvocation.InvocationName -ne '.') {
    try {
        if(!$GamePath){
            if($NoUI){throw 'Informe -GamePath'}
            Add-Type -AssemblyName System.Windows.Forms
            $picker=New-Object Windows.Forms.FolderBrowserDialog
            $picker.Description='ForgeLoader - escolha a pasta do Kingdoms Reborn'
            $picker.ShowNewFolderButton=$false
            if($picker.ShowDialog() -ne [Windows.Forms.DialogResult]::OK){exit 0}
            $GamePath=$picker.SelectedPath;$picker.Dispose()
        }
        $layout=Get-Layout $GamePath
        if($Mode -eq 'Install'){$result=Invoke-Install $layout $SavedPath}
        elseif($Mode -eq 'Restore'){$result=Invoke-Restore $layout $SavedPath}
        else{$result=@{status='inspected';exe_sha256=(Get-BytesHash ([IO.File]::ReadAllBytes($layout.Exe)))}}
        if($NoUI){$result | ConvertTo-Json}else{Add-Type -AssemblyName System.Windows.Forms;[Windows.Forms.MessageBox]::Show($result.message,'ForgeLoader')|Out-Null}
    }catch{
        if($NoUI){[Console]::Error.WriteLine($_.Exception.Message)}else{Add-Type -AssemblyName System.Windows.Forms;[Windows.Forms.MessageBox]::Show($_.Exception.Message,'ForgeLoader',0,16)|Out-Null}
        exit 1
    }
}
