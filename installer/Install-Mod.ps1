param([string]$GamePath,[string]$Package,[switch]$NoUI)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
function Install-ForgeMod([string]$Root,[string]$Archive) {
    $rootPath=[IO.Path]::GetFullPath($Root)
    if(!(Test-Path -LiteralPath (Join-Path $rootPath 'PunCity\Binaries\Win64\KingdomsPortraits.dll') -PathType Leaf)){throw 'Instale o ForgeLoader 0.2 primeiro nesta pasta do jogo.'}
    $archivePath=[IO.Path]::GetFullPath($Archive)
    if([IO.Path]::GetExtension($archivePath) -notin @('.flmod','.zip')){throw 'Escolha um arquivo .flmod ou ZIP de mod ForgeLoader.'}
    if((Get-Item -LiteralPath $archivePath).Length -gt 32MB){throw 'Pacote excede 32 MB.'}
    $zip=[IO.Compression.ZipFile]::OpenRead($archivePath)
    $staging=$null
    try {
        if($zip.Entries.Count -gt 1000){throw 'Pacote tem arquivos demais.'}
        $names=@{};$total=0L
        foreach($entry in $zip.Entries){
            $name=$entry.FullName
            if(!$name -or $name.Contains('\') -or $name.Contains(':') -or $name.StartsWith('/') -or (($entry.ExternalAttributes -shr 16) -band 0xF000) -eq 0xA000){throw 'Caminho ou link invalido no pacote.'}
            foreach($part in $name.TrimEnd('/').Split('/')){if(!$part -or $part -in @('.','..') -or $part -match '[<>"|?*\x00-\x1f]' -or $part.EndsWith('.') -or $part.EndsWith(' ') -or $part -match '^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)'){throw 'Nome de arquivo invalido no pacote.'}}
            $key=$name.TrimEnd('/').ToLowerInvariant();if($names.ContainsKey($key)){throw 'Caminho duplicado no pacote.'};$names[$key]=$true
            $total+=$entry.Length;if($total -gt 32MB -or $entry.Length -gt 16MB){throw 'Conteudo descompactado excede o limite.'}
        }
        $manifestEntry=$zip.GetEntry('mod.json');if(!$manifestEntry -or $manifestEntry.Length -gt 65536){throw 'O pacote precisa de mod.json na raiz. Nao selecione o ZIP do Dev Kit.'}
        $reader=New-Object IO.StreamReader($manifestEntry.Open(),[Text.Encoding]::UTF8)
        try {$manifest=$reader.ReadToEnd() | ConvertFrom-Json} finally {$reader.Dispose()}
        if($manifest.schema -ne 1 -or $manifest.api_major -ne 1 -or $manifest.id -notmatch '^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$' -or $manifest.id.StartsWith('core.')){throw 'Manifesto ForgeLoader invalido.'}
        if($manifest.version -notmatch '^\d+\.\d+\.\d+$' -or !$manifest.name){throw 'Nome ou versao do mod invalido.'}
        if($manifest.runtime -notin @('forgeloader-lua','forgeloader-native')){throw 'Este mod usa outro runtime. Use um mod feito para ForgeLoader 0.2.'}
        if($manifest.multiplayer -ne 'local'){throw 'Esta versao ainda nao carrega mods de simulacao compartilhada; a negociacao multiplayer esta em desenvolvimento.'}
        if($manifest.game_builds -notcontains 'a5d2385660d9e819d2aa073cdd9c1d74c05149c9617f37cbb8b31e83708c4e24'){throw 'Mod nao declara compatibilidade com o build suportado.'}
        if(!$manifest.entrypoint -or !$names.ContainsKey($manifest.entrypoint.ToLowerInvariant()) -or $manifest.entrypoint.EndsWith('/')){throw 'Arquivo de entrada ausente.'}
        $mods=Join-Path $rootPath 'Mods';[IO.Directory]::CreateDirectory($mods)|Out-Null
        if((Get-Item -LiteralPath $mods).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Mods deve ser uma pasta normal, sem redirecionamento.'}
        $destination=Join-Path $mods $manifest.id
        if(Test-Path -LiteralPath $destination){throw ('O mod '+$manifest.id+' ja existe. Feche o jogo e mova a pasta antiga de Mods antes de instalar esta versao.')}
        $stagingRoot=Join-Path $rootPath 'ForgeLoader\Staging';[IO.Directory]::CreateDirectory($stagingRoot)|Out-Null
        if((Get-Item -LiteralPath $stagingRoot).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Pasta de instalacao redirecionada.'}
        $staging=Join-Path $stagingRoot ([guid]::NewGuid().ToString('N'));[IO.Directory]::CreateDirectory($staging)|Out-Null
        $prefix=[IO.Path]::GetFullPath($staging)+[IO.Path]::DirectorySeparatorChar
        foreach($entry in $zip.Entries){
            $target=[IO.Path]::GetFullPath((Join-Path $staging $entry.FullName))
            if(!$target.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Arquivo fora da pasta do mod.'}
            if($entry.FullName.EndsWith('/')){[IO.Directory]::CreateDirectory($target)|Out-Null}else{[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))|Out-Null;[IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$target,$false)}
        }
        [IO.Directory]::Move($staging,$destination);$staging=$null
        return @{status='installed';id=$manifest.id;folder=$destination;message=($manifest.name+' instalado! Reinicie o jogo e clique em Meus mods.')}
    }finally{
        $zip.Dispose()
        if($staging -and (Test-Path -LiteralPath $staging)){
            $resolved=[IO.Path]::GetFullPath($staging);$allowed=[IO.Path]::GetFullPath((Join-Path $rootPath 'ForgeLoader\Staging'))+[IO.Path]::DirectorySeparatorChar
            if($resolved.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase)){Remove-Item -LiteralPath $resolved -Recurse -Force}
        }
    }
}
if($MyInvocation.InvocationName -ne '.'){
    try{
        if((!$GamePath -or !(Test-Path -LiteralPath (Join-Path $GamePath 'PunCity\Binaries\Win64\KingdomsPortraits.dll') -PathType Leaf)) -and !$NoUI){
            Add-Type -AssemblyName System.Windows.Forms;$folder=New-Object Windows.Forms.FolderBrowserDialog;$folder.Description='Escolha a pasta do Kingdoms Reborn com ForgeLoader instalado';$folder.ShowNewFolderButton=$false
            if($folder.ShowDialog() -ne 'OK'){exit 0};$GamePath=$folder.SelectedPath;$folder.Dispose()
        }
        if(!$Package -and !$NoUI){Add-Type -AssemblyName System.Windows.Forms;$picker=New-Object Windows.Forms.OpenFileDialog;$picker.Title='Instalar mod ForgeLoader';$picker.Filter='Mods ForgeLoader (*.flmod;*.zip)|*.flmod;*.zip';if($picker.ShowDialog() -ne 'OK'){exit 0};$Package=$picker.FileName;$picker.Dispose()}
        if(!$GamePath -or !$Package){throw 'Informe a pasta do jogo e o arquivo .flmod.'}
        $result=Install-ForgeMod $GamePath $Package
        if($NoUI){$result|ConvertTo-Json}else{Add-Type -AssemblyName System.Windows.Forms;[Windows.Forms.MessageBox]::Show($result.message,'ForgeLoader')|Out-Null}
    }catch{if($NoUI){[Console]::Error.WriteLine($_.Exception.Message)}else{Add-Type -AssemblyName System.Windows.Forms;[Windows.Forms.MessageBox]::Show($_.Exception.Message,'ForgeLoader',0,16)|Out-Null};exit 1}
}
