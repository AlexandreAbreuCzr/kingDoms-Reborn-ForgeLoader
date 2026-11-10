# Initialize pinned REA submodules while omitting unrepresentable Linux fixtures.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$rea = Join-Path $root 'tools\rea'
function Invoke-Git([string[]]$Arguments) {
    & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw ('git failed: ' + ($Arguments -join ' ')) }
}
Invoke-Git @('-C',$root,'submodule','update','--init','tools/rea')
Invoke-Git @('-C',$rea,'submodule','init')
foreach ($name in @('binwalk','ghidra-nativeaot','jadx-headless-mcp','wakaru')) {
    Invoke-Git @('-C',$rea,'submodule','update','--init','--recursive',('third_party/' + $name))
}
$unblob = Join-Path $rea 'third_party\unblob'
if (-not (Test-Path -LiteralPath (Join-Path $unblob '.git'))) {
    Invoke-Git @('clone','--no-checkout','https://github.com/onekey-sec/unblob.git',$unblob)
    Invoke-Git @('-C',$rea,'submodule','absorbgitdirs','third_party/unblob')
}
Invoke-Git @('-C',$unblob,'sparse-checkout','init','--no-cone')
@('/*','!/tests/') | & git -C $unblob -c core.protectNTFS=false sparse-checkout set --no-cone --stdin
if ($LASTEXITCODE -ne 0) { throw 'Unable to set Unblob sparse checkout.' }
$entry = & git -C $rea ls-tree HEAD third_party/unblob
if ($LASTEXITCODE -ne 0 -or $entry -notmatch '^160000 commit ([0-9a-f]{40})') { throw 'Unblob gitlink not found.' }
$revision = $Matches[1]
# Git for Windows validates excluded Linux names too. This per-command setting
# admits their index entries; sparse checkout keeps them out of the NTFS tree.
Invoke-Git @('-C',$unblob,'-c','core.protectNTFS=false','checkout','--detach',$revision)
Invoke-Git @('-C',$rea,'submodule','update','--init','--recursive')
Invoke-Git @('-C',$rea,'submodule','status','--recursive')
