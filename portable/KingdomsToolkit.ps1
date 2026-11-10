# Windows PowerShell 5.1; no administrator, Python or REA runtime required.
[CmdletBinding()]
param(
    [ValidateSet('Diagnose','Apply','Restore','Launch','Compatibility','NoAsync','PatchAsync','RestorePatch')]
    [string]$Mode = 'Diagnose',
    [string]$GamePath,
    [string]$SavedPath = (Join-Path $env:LOCALAPPDATA 'PunCity\Saved'),
    [string]$DataPath,
    [string]$ProfilePath,
    [string]$BackupDirectory
)
$ErrorActionPreference = 'Stop'
if (-not $DataPath) { $DataPath = Join-Path $PSScriptRoot 'Dados' }
if (-not $ProfilePath) { $ProfilePath = Join-Path $PSScriptRoot 'startup-safe.json' }
$utf8 = New-Object System.Text.UTF8Encoding($false)
$allowedNames = @('Engine.ini','GameUserSettings.ini')

function Write-JsonFile($Path, $Value) {
    [IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 12), $utf8)
}
function Get-HashBytes([byte[]]$Bytes) {
    $hasher = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hasher.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() }
    finally { $hasher.Dispose() }
}
function Get-HashFile([string]$Path) {
    $hasher=[Security.Cryptography.SHA256]::Create()
    $stream=[IO.File]::OpenRead($Path)
    try { return ([BitConverter]::ToString($hasher.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $hasher.Dispose() }
}
function Assert-GameClosed {
    if (Get-Process -Name 'PrototypeCity-Win64-Shipping','KingdomsReborn' -ErrorAction SilentlyContinue) {
        throw 'Feche Kingdoms Reborn antes de aplicar ou restaurar o perfil.'
    }
}
function Get-NewFolder([string]$Prefix) {
    $name = '{0}-{1}-{2}' -f $Prefix,(Get-Date -Format 'yyyyMMdd-HHmmss'),([guid]::NewGuid().ToString('N').Substring(0,8))
    $folder = Join-Path $DataPath $name
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    return $folder
}
function Resolve-Game {
    $candidates = @($GamePath, $PSScriptRoot, (Split-Path $PSScriptRoot -Parent), (Join-Path $env:USERPROFILE 'Downloads\Kingdoms Reborn'))
    $steam = Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue
    if ($steam -and $steam.SteamPath) { $candidates += Join-Path $steam.SteamPath 'steamapps\common\Kingdoms Reborn' }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath (Join-Path $candidate 'KingdomsReborn.exe') -PathType Leaf)) {
            return (Get-Item -LiteralPath $candidate).FullName
        }
    }
    $entered = (Read-Host 'Cole o caminho da pasta que contem KingdomsReborn.exe (Enter para cancelar)').Trim().Trim('"')
    if (-not $entered) { throw 'Pasta do jogo nao selecionada.' }
    if (-not (Test-Path -LiteralPath (Join-Path $entered 'KingdomsReborn.exe') -PathType Leaf)) { throw 'KingdomsReborn.exe nao encontrado nessa pasta.' }
    return (Get-Item -LiteralPath $entered).FullName
}
function Update-Ini([string]$Text, $Sections) {
    $newline = "`n"
    if ($Text.Contains("`r`n")) { $newline = "`r`n" }
    foreach ($section in $Sections.PSObject.Properties) {
        $pattern = '(?ims)^\s*\[' + [regex]::Escape($section.Name) + '\][^\r\n]*(?:\r?\n|$)(?:(?!^[\t ]*\[)[\s\S])*'
        $matches = [regex]::Matches($Text, $pattern)
        if ($matches.Count -gt 1) { throw ('Secao INI duplicada: ' + $section.Name + '. Revise antes de aplicar.') }
        if ($matches.Count -eq 0) {
            if ($Text.Length -gt 0 -and -not $Text.EndsWith("`n")) { $Text += $newline }
            $Text += $newline + '[' + $section.Name + ']' + $newline
            $matches = [regex]::Matches($Text, $pattern)
        }
        $match = $matches[0]
        $block = $match.Value
        foreach ($entry in $section.Value.PSObject.Properties) {
            $keyPattern = '(?im)^([\t ]*' + [regex]::Escape($entry.Name) + '[\t ]*=)[^\r\n]*'
            if ([regex]::IsMatch($block, $keyPattern)) {
                $replacement = '${1}' + [string]$entry.Value
                $block = [regex]::Replace($block, $keyPattern, $replacement)
            } else {
                if (-not $block.EndsWith("`n")) { $block += $newline }
                $block += $entry.Name + '=' + [string]$entry.Value + $newline
            }
        }
        $Text = $Text.Substring(0,$match.Index) + $block + $Text.Substring($match.Index+$match.Length)
    }
    return $Text
}
function Get-IniEdit([string]$Path, $Sections) {
    $bytes = [byte[]]@()
    if (Test-Path -LiteralPath $Path) { $bytes = [IO.File]::ReadAllBytes($Path) }
    $encoding = $utf8
    $skip = 0
    $bom = [byte[]]@()
    if ($bytes.Length -ge 2 -and $bytes[0] -eq 255 -and $bytes[1] -eq 254) {
        $encoding = [Text.Encoding]::Unicode; $skip = 2; $bom = [byte[]]@(255,254)
    } elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 254 -and $bytes[1] -eq 255) {
        $encoding = [Text.Encoding]::BigEndianUnicode; $skip = 2; $bom = [byte[]]@(254,255)
    } elseif ($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) {
        $skip = 3; $bom = [byte[]]@(239,187,191)
    } else {
        $strict = New-Object Text.UTF8Encoding($false,$true)
        try { $null = $strict.GetString($bytes) } catch { $encoding = [Text.Encoding]::GetEncoding(1252) }
    }
    $text = $encoding.GetString($bytes,$skip,$bytes.Length-$skip)
    $changed = Update-Ini $text $Sections
    $after = [byte[]]($bom + $encoding.GetBytes($changed))
    return [pscustomobject]@{Path=$Path; Before=$bytes; After=$after; Existed=(Test-Path -LiteralPath $Path)}
}
function Apply-Profile {
    Assert-GameClosed
    $profile = Get-Content -LiteralPath $ProfilePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $config = Join-Path ([IO.Path]::GetFullPath($SavedPath)) 'Config\WindowsNoEditor'
    $edits = @()
    foreach ($file in $profile.PSObject.Properties) {
        if ($file.Name -notin $allowedNames) { throw 'Perfil contem nome de arquivo nao permitido.' }
        $edit = Get-IniEdit (Join-Path $config $file.Name) $file.Value
        if ((Get-HashBytes $edit.Before) -ne (Get-HashBytes $edit.After)) { $edits += $edit }
    }
    if ($edits.Count -eq 0) { Write-Host 'Perfil ja aplicado. Nada alterado.'; return }
    $backup = Get-NewFolder 'backup'
    $manifest = [ordered]@{createdAt=(Get-Date -Format o); configDirectory=$config; state='prepared'; files=@()}
    foreach ($edit in $edits) {
        $name = Split-Path $edit.Path -Leaf
        if ($edit.Existed) { [IO.File]::WriteAllBytes((Join-Path $backup $name), $edit.Before) }
        $manifest.files += [ordered]@{name=$name; existed=$edit.Existed; beforeHash=(Get-HashBytes $edit.Before); afterHash=(Get-HashBytes $edit.After)}
    }
    Write-JsonFile (Join-Path $backup 'manifest.json') $manifest
    New-Item -ItemType Directory -Path $config -Force | Out-Null
    foreach ($edit in $edits) {
        if ((Test-Path -LiteralPath $edit.Path) -ne $edit.Existed) { throw 'Configuracao mudou durante a aplicacao. Backup preservado.' }
        if ($edit.Existed -and (Get-HashBytes ([IO.File]::ReadAllBytes($edit.Path))) -ne (Get-HashBytes $edit.Before)) { throw 'Configuracao mudou durante a aplicacao. Backup preservado.' }
        [IO.File]::WriteAllBytes($edit.Path,$edit.After)
    }
    $manifest.state = 'applied'
    Write-JsonFile (Join-Path $backup 'manifest.json') $manifest
    Write-Host ('Perfil aplicado: janela 1280x720, limite de 45 FPS, qualidade reduzida. Backup: ' + $backup)
}
function Restore-Profile {
    Assert-GameClosed
    $backup = $BackupDirectory
    if (-not $backup) {
        $folders = @(Get-ChildItem -LiteralPath $DataPath -Directory -Filter 'backup-*' -ErrorAction SilentlyContinue | Sort-Object Name -Descending)
        $selected = $folders | Where-Object {
            $m = Join-Path $_.FullName 'manifest.json'
            (Test-Path -LiteralPath $m) -and ((Get-Content -LiteralPath $m -Raw | ConvertFrom-Json).state -ne 'restored')
        } | Select-Object -First 1
        if (-not $selected) { throw 'Nenhum backup pendente de restauracao nesta pasta Dados.' }
        $backup = $selected.FullName
    }
    $manifest = Get-Content -LiteralPath (Join-Path $backup 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $config = Join-Path ([IO.Path]::GetFullPath($SavedPath)) 'Config\WindowsNoEditor'
    if ($config -ne $manifest.configDirectory) { throw 'Este backup pertence a outro usuario ou pasta de configuracao.' }
    foreach ($item in $manifest.files) {
        if ($item.name -notin $allowedNames) { throw 'Nome de arquivo inesperado no backup.' }
        if ($item.existed -and (Get-HashBytes ([IO.File]::ReadAllBytes((Join-Path $backup $item.name)))) -ne $item.beforeHash) { throw 'Backup danificado; restauracao cancelada.' }
    }
    $safety = Get-NewFolder 'antes-de-restaurar'
    foreach ($item in $manifest.files) {
        $target = Join-Path $config $item.name
        if (Test-Path -LiteralPath $target) { Copy-Item -LiteralPath $target -Destination (Join-Path $safety $item.name) }
    }
    foreach ($item in $manifest.files) {
        $target = Join-Path $config $item.name
        if ($item.existed) { [IO.File]::WriteAllBytes($target,[IO.File]::ReadAllBytes((Join-Path $backup $item.name))) }
        elseif (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target }
    }
    $manifest.state = 'restored'
    Write-JsonFile (Join-Path $backup 'manifest.json') $manifest
    Write-Host ('Configuracao anterior restaurada. Estado mais recente preservado em: ' + $safety)
}
function Get-PatchSpec {
    $spec = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'noasync-binary-patch.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($spec.id -ne 'd3d11-noasync-v1' -or $spec.target_relative_path -ne 'PunCity/Binaries/Win64/PrototypeCity-Win64-Shipping.exe') { throw 'Manifesto de patch inesperado.' }
    return $spec
}
function Convert-HexBytes([string]$Hex) {
    if ($Hex.Length % 2 -ne 0 -or $Hex -notmatch '^[0-9a-f]+$') { throw 'Bytes de patch invalidos.' }
    $bytes = New-Object byte[] ($Hex.Length / 2)
    for ($i=0; $i -lt $bytes.Length; $i++) { $bytes[$i]=[Convert]::ToByte($Hex.Substring($i*2,2),16) }
    return ,$bytes
}
function Apply-BinaryPatch {
    Assert-GameClosed
    $game = Resolve-Game
    $spec = Get-PatchSpec
    $target = Join-Path $game $spec.target_relative_path
    $raw = [IO.File]::ReadAllBytes($target)
    $hash = Get-HashBytes $raw
    if ($hash -eq $spec.patched_sha256) { Write-Host 'Patch NoAsync ja aplicado. Nada alterado.'; return }
    if ($hash -ne $spec.source_sha256 -or $raw.Length -ne $spec.size) { throw 'Executavel diferente da versao analisada. Patch recusado; nenhum arquivo alterado.' }
    $before = Convert-HexBytes $spec.original_hex
    $after = Convert-HexBytes $spec.patched_hex
    $offset = [int]$spec.file_offset
    if ($before.Length -ne $after.Length -or $offset -lt 0 -or ($offset+$before.Length) -gt $raw.Length) { throw 'Intervalo de patch invalido.' }
    for ($i=0; $i -lt $before.Length; $i++) { if ($raw[$offset+$i] -ne $before[$i]) { throw 'Instrucoes originais nao correspondem. Patch recusado.' } }
    $patched = [byte[]]$raw.Clone()
    [Array]::Copy($after,0,$patched,$offset,$after.Length)
    if ((Get-HashBytes $patched) -ne $spec.patched_sha256) { throw 'Checksum do patch incorreto. Nenhum arquivo alterado.' }
    $backup = Get-NewFolder 'binary-backup'
    $original = Join-Path $backup 'PrototypeCity-Win64-Shipping.exe'
    [IO.File]::WriteAllBytes($original,$raw)
    if ((Get-HashFile $original) -ne $spec.source_sha256) { throw 'Falha ao verificar backup. Original preservado.' }
    $manifest = [ordered]@{patchId=$spec.id; target=$target; createdAt=(Get-Date -Format o); state='prepared'; originalHash=$spec.source_sha256; patchedHash=$spec.patched_sha256; fileOffset=$offset; changedBytes=$after.Length}
    Write-JsonFile (Join-Path $backup 'binary-manifest.json') $manifest
    $temporary = $target + '.noasync-' + [guid]::NewGuid().ToString('N') + '.tmp'
    try {
        [IO.File]::WriteAllBytes($temporary,$patched)
        if ((Get-HashFile $target) -ne $spec.source_sha256) { throw 'Executavel mudou durante a operacao. Patch cancelado.' }
        [IO.File]::Replace($temporary,$target,[System.Management.Automation.Language.NullString]::Value)
    } finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary } }
    $manifest.state='applied'
    Write-JsonFile (Join-Path $backup 'binary-manifest.json') $manifest
    Write-Host ('Patch experimental aplicado: 4 bytes em uma funcao. Backup: ' + $backup)
    Write-Host 'Ele desativa criacao assincrona D3D11; nao ignora erros nem recupera um dispositivo perdido.'
}
function Restore-BinaryPatch {
    Assert-GameClosed
    $game=Resolve-Game
    $spec=Get-PatchSpec
    $target=Join-Path $game $spec.target_relative_path
    $hash=Get-HashFile $target
    if ($hash -eq $spec.source_sha256) { Write-Host 'Executavel ja esta original.'; return }
    if ($hash -ne $spec.patched_sha256) { throw 'Executavel foi alterado ou atualizado. Restauracao automatica recusada para preservar essa versao.' }
    $folders=@(Get-ChildItem -LiteralPath $DataPath -Directory -Filter 'binary-backup-*' -ErrorAction SilentlyContinue | Sort-Object Name -Descending)
    $selected=$folders | Where-Object {
        $path=Join-Path $_.FullName 'binary-manifest.json'
        if (Test-Path -LiteralPath $path) { $m=Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json; $m.target -eq $target -and $m.patchId -eq $spec.id -and $m.state -ne 'restored' }
    } | Select-Object -First 1
    if (-not $selected) { throw 'Backup original desse executavel nao encontrado na pasta Dados.' }
    $original=Join-Path $selected.FullName 'PrototypeCity-Win64-Shipping.exe'
    if ((Get-HashFile $original) -ne $spec.source_sha256) { throw 'Backup binario danificado. Restauracao cancelada.' }
    $temporary=$target + '.restore-' + [guid]::NewGuid().ToString('N') + '.tmp'
    try {
        Copy-Item -LiteralPath $original -Destination $temporary
        [IO.File]::Replace($temporary,$target,[System.Management.Automation.Language.NullString]::Value)
    } finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary } }
    $path=Join-Path $selected.FullName 'binary-manifest.json'
    $manifest=Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    $manifest.state='restored'; Write-JsonFile $path $manifest
    Write-Host 'Executavel original restaurado e checksum conferido.'
}
function Collect-Diagnostics {
    $game = Resolve-Game
    $folder = Get-NewFolder 'diagnostico'
    $report = [ordered]@{collectedAt=(Get-Date -Format o); gamePath=$game; savedPath=$SavedPath; gpu=@(); cpu=@(); crashes=@(); files=@(); limitations=@('Nao mede FPS, temperaturas ou estabilidade.','AdapterRAM do WMI tem 32 bits; nao representa com confianca VRAM acima de 4 GB.','Crashes e configuracoes podem conter caminhos e identificadores pessoais. Arquivos ficam locais.')}
    $report.gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,DriverDate,AdapterRAM,PNPDeviceID)
    $report.cpu = @(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors)
    $report.os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,TotalVisibleMemorySize,FreePhysicalMemory,TotalVirtualMemorySize,FreeVirtualMemory
    $report.disks = @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID,Size,FreeSpace)
    foreach ($relative in @('KingdomsReborn.exe','PunCity\Binaries\Win64\PrototypeCity-Win64-Shipping.exe')) {
        $path = Join-Path $game $relative
        if (Test-Path -LiteralPath $path) { $report.files += [ordered]@{path=$relative; bytes=(Get-Item -LiteralPath $path).Length; sha256=(Get-HashFile $path)} }
    }
    foreach ($name in $allowedNames) {
        $path = Join-Path $SavedPath ('Config\WindowsNoEditor\' + $name)
        if (Test-Path -LiteralPath $path) { Copy-Item -LiteralPath $path -Destination (Join-Path $folder $name) }
    }
    $crashFiles = @(Get-ChildItem -LiteralPath (Join-Path $SavedPath 'Crashes') -Filter 'CrashContext.runtime-xml' -Recurse -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 10)
    foreach ($crash in $crashFiles) {
        try {
            $readerSettings = New-Object Xml.XmlReaderSettings
            $readerSettings.DtdProcessing = [Xml.DtdProcessing]::Prohibit
            $readerSettings.XmlResolver = $null
            $reader = [Xml.XmlReader]::Create($crash.FullName,$readerSettings)
            try { $xml = New-Object Xml.XmlDocument; $xml.XmlResolver=$null; $xml.Load($reader) } finally { $reader.Dispose() }
            $props = $xml.FGenericCrashContext.RuntimeProperties
            $report.crashes += [ordered]@{modifiedAt=$crash.LastWriteTime.ToString('o'); engine=[string]$props.EngineVersion; error=[string]$props.ErrorMessage; stack=[string]$props.CallStack; gpu=[string]$props.'Misc.PrimaryGPUBrand'; seconds=[string]$props.SecondsSinceStart; oom=[string]$props.'MemoryStats.bIsOOM'}
        } catch { $report.crashes += @{file=$crash.Name; parseError=$_.Exception.Message} }
    }
    try {
        $events = @(Get-WinEvent -FilterHashtable @{LogName='System';Id=4101;StartTime=(Get-Date).AddDays(-7)} -MaxEvents 20 -ErrorAction Stop | Select-Object TimeCreated,Id,ProviderName,Message)
        Write-JsonFile (Join-Path $folder 'display-events.json') $events
    } catch { $report.displayEventsStatus = $_.Exception.Message }
    try {
        $events = @(Get-WinEvent -FilterHashtable @{LogName='Application';Id=1000,1001;StartTime=(Get-Date).AddDays(-7)} -MaxEvents 200 -ErrorAction Stop | Where-Object {$_.Message -match 'PrototypeCity|PunCity|Kingdoms|LiveKernelEvent'} | Select-Object TimeCreated,Id,ProviderName,Message)
        Write-JsonFile (Join-Path $folder 'application-events.json') $events
    } catch { $report.applicationEventsStatus = $_.Exception.Message }
    $nvidia = Get-Command 'nvidia-smi.exe' -ErrorAction SilentlyContinue
    if ($nvidia) {
        try { & $nvidia.Source '--query-gpu=name,driver_version,memory.total,temperature.gpu' '--format=csv' 2>&1 | Out-File -LiteralPath (Join-Path $folder 'nvidia-gpu.txt') -Encoding utf8 } catch { $report.nvidiaSmiStatus=$_.Exception.Message }
    }
    Write-JsonFile (Join-Path $folder 'diagnostico.json') $report
    $archive = $folder + '.zip'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::CreateFromDirectory([IO.Path]::GetFullPath($folder),[IO.Path]::GetFullPath($archive))
    Write-Host ('Diagnostico salvo localmente: ' + $archive)
    Write-Host 'Nenhum arquivo foi enviado. Revise os caminhos e identificadores antes de compartilhar.'
}

try {
    New-Item -ItemType Directory -Path $DataPath -Force | Out-Null
    switch ($Mode) {
        'Diagnose' { Collect-Diagnostics }
        'Apply' { Apply-Profile }
        'Restore' { Restore-Profile }
        'PatchAsync' { Apply-BinaryPatch }
        'RestorePatch' { Restore-BinaryPatch }
        {$_ -in 'Launch','Compatibility','NoAsync'} {
            Assert-GameClosed
            $game = Resolve-Game
            if (-not (Get-Process -Name 'steam' -ErrorAction SilentlyContinue)) { throw 'Abra o Steam e depois tente iniciar o jogo novamente.' }
            Apply-Profile
            $arguments = @('-windowed','-ResX=1280','-ResY=720')
            if ($Mode -eq 'Compatibility') { $arguments += '-norhithread'; Write-Host 'Teste experimental: sem thread RHI separada. Pode reduzir o desempenho.' }
            if ($Mode -eq 'NoAsync') { $arguments += '-nod3dasync'; Write-Host 'Teste baseado no binario: desativa criacao assincrona de recursos D3D11.' }
            $before = @{}
            Get-ChildItem -LiteralPath (Join-Path $SavedPath 'Crashes') -Filter 'CrashContext.runtime-xml' -Recurse -ErrorAction SilentlyContinue | ForEach-Object { $before[$_.FullName]=$_.LastWriteTimeUtc.Ticks }
            $started = Get-Date
            $session = Get-NewFolder 'sessao'
            Write-JsonFile (Join-Path $session 'inicio.json') ([ordered]@{startedAt=$started.ToString('o'); mode=$Mode; arguments=$arguments; target=(Join-Path $game 'KingdomsReborn.exe')})
            $launch = Start-Process -FilePath (Join-Path $game 'KingdomsReborn.exe') -WorkingDirectory $game -ArgumentList $arguments -PassThru
            Start-Sleep -Milliseconds 300
            try {
                $targetPath=[IO.Path]::GetFullPath((Join-Path $game 'PunCity\Binaries\Win64\PrototypeCity-Win64-Shipping.exe'))
                $children=@(Get-CimInstance Win32_Process -Filter "Name='PrototypeCity-Win64-Shipping.exe'" | Where-Object { $_.ParentProcessId -eq $launch.Id -and $_.ExecutablePath -eq $targetPath } | Select-Object ProcessId,CreationDate,ExecutablePath,CommandLine)
                Write-JsonFile (Join-Path $session 'comando-observado.json') ([ordered]@{observedAt=(Get-Date -Format o); children=$children; noAsyncObserved=(@($children | Where-Object { $_.CommandLine -match '(?i)(?:^|\s)-nod3dasync(?:\s|$)' }).Count -gt 0); limitation='Consulta pontual; ausencia do processo nao prova que a opcao foi perdida.'})
            } catch { Write-JsonFile (Join-Path $session 'comando-observado.json') @{status='unknown'; reason=$_.Exception.Message} }
            Write-Host 'Jogo iniciado. O resultado precisa ser confirmado visualmente no menu.'
            Write-Host 'Aguardando encerramento para coletar o diagnostico. Deixe esta janela aberta.'
            $launch.WaitForExit()
            $fresh = @(Get-ChildItem -LiteralPath (Join-Path $SavedPath 'Crashes') -Filter 'CrashContext.runtime-xml' -Recurse -ErrorAction SilentlyContinue | Where-Object { -not $before.ContainsKey($_.FullName) -or $before[$_.FullName] -ne $_.LastWriteTimeUtc.Ticks } | Select-Object FullName,LastWriteTime)
            Write-JsonFile (Join-Path $session 'sessao.json') ([ordered]@{startedAt=$started.ToString('o'); endedAt=(Get-Date -Format o); mode=$Mode; arguments=$arguments; bootstrapExitCode=$launch.ExitCode; newCrashContexts=$fresh; limitation='Ausencia de crash e codigo do bootstrap nao comprovam estabilidade nem chegada ao menu.'})
            $GamePath = $game
            Collect-Diagnostics
        }
    }
    exit 0
} catch {
    Write-Host ('ERRO: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
