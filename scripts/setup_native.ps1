# Fetch only the pinned native hooking dependency into the ignored local folder.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$commit=(Get-Content (Join-Path $root 'release.json') -Raw | ConvertFrom-Json).minhook_commit
$destination=Join-Path $root '.local/minhook'
if(!(Test-Path -LiteralPath $destination)){
    & git clone --no-checkout https://github.com/TsudaKageyu/minhook.git $destination
    if($LASTEXITCODE -ne 0){throw 'MinHook clone failed'}
    & git -C $destination checkout --detach $commit
    if($LASTEXITCODE -ne 0){throw 'MinHook checkout failed'}
}
$actual=& git -C $destination rev-parse HEAD
if($LASTEXITCODE -ne 0 -or $actual -ne $commit){throw 'Existing MinHook differs from pinned revision; preserved'}
Write-Output ('MinHook verified: '+$actual)
