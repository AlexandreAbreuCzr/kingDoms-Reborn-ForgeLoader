$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$vswhere=Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if(!(Test-Path -LiteralPath $vswhere)){throw 'Install Visual Studio C++ Build Tools first'}
$vsPath=& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if(!$vsPath){throw 'MSVC x64 tools not found'}
$msvc=(Get-ChildItem -LiteralPath (Join-Path $vsPath 'VC\Tools\MSVC') -Directory | Sort-Object Name -Descending | Select-Object -First 1).FullName
$sdk='C:\Program Files (x86)\Windows Kits\10'
$sdkVersion=(Get-ChildItem -LiteralPath (Join-Path $sdk 'Include') -Directory | Where-Object {Test-Path -LiteralPath (Join-Path $_.FullName 'um\windows.h')} | Sort-Object Name -Descending | Select-Object -First 1).Name
if(!$sdkVersion){throw 'Windows SDK not found'}
$env:INCLUDE="$msvc\include;$sdk\Include\$sdkVersion\ucrt;$sdk\Include\$sdkVersion\shared;$sdk\Include\$sdkVersion\um"
$env:LIB="$msvc\lib\x64;$sdk\Lib\$sdkVersion\ucrt\x64;$sdk\Lib\$sdkVersion\um\x64"
$env:PATH="$msvc\bin\Hostx64\x64;$env:PATH"
$output=Join-Path $root '.local\portrait-build'
New-Item -ItemType Directory -Path $output -Force | Out-Null
Push-Location $output
try {
    & python "$root\scripts\setup_loader.py"
    if($LASTEXITCODE -ne 0){throw 'Loader dependency setup failed'}
    $lua=Join-Path $root '.local\loader-deps\lua-5.4.9\src'
    $luaSources=@(Get-ChildItem -LiteralPath $lua -Filter '*.c' | Where-Object {$_.Name -notin @('lua.c','luac.c')} | ForEach-Object {$_.FullName})
    & "$msvc\bin\Hostx64\x64\cl.exe" /nologo /c /O2 /MT /TC "/I$lua" $luaSources
    if($LASTEXITCODE -ne 0){throw 'Lua compilation failed'}
    $luaObjects=@($luaSources | ForEach-Object {[IO.Path]::GetFileNameWithoutExtension($_)+'.obj'})
    & "$msvc\bin\Hostx64\x64\lib.exe" /nologo /OUT:forge-lua.lib $luaObjects
    if($LASTEXITCODE -ne 0){throw 'Lua static library failed'}
    & "$msvc\bin\Hostx64\x64\cl.exe" /nologo /c /O2 /MT /EHsc /std:c++17 /W4 "/I$lua" "/I$root\.local\loader-deps" "$root\native\loader\loader.cpp"
    if($LASTEXITCODE -ne 0){throw 'Mod loader compilation failed'}
    & "$msvc\bin\Hostx64\x64\cl.exe" /nologo /c /O2 /MT /TC "/I$root\.local\minhook\include" "/I$root\.local\minhook\src" "$root\.local\minhook\src\buffer.c" "$root\.local\minhook\src\hook.c" "$root\.local\minhook\src\trampoline.c" "$root\.local\minhook\src\hde\hde64.c"
    if($LASTEXITCODE -ne 0){throw 'MinHook compilation failed'}
    & "$msvc\bin\Hostx64\x64\cl.exe" /nologo /LD /O2 /MT /EHsc /std:c++17 /W4 "/I$root\.local\minhook\include" "$root\native\portraits\portraits.cpp" loader.obj forge-lua.lib buffer.obj hook.obj trampoline.obj hde64.obj /link /Brepro /OUT:KingdomsPortraits.dll user32.lib gdi32.lib
    if($LASTEXITCODE -ne 0){throw 'Portrait runtime compilation failed'}
    & "$msvc\bin\Hostx64\x64\cl.exe" /nologo /O2 /MD /EHsc /std:c++17 "$root\native\portraits\protocol_test.cpp" /Fe:protocol_test.exe
    if($LASTEXITCODE -ne 0){throw 'Protocol tests compilation failed'}
    & .\protocol_test.exe
    if($LASTEXITCODE -ne 0){throw 'Protocol tests failed'}
    & "$msvc\bin\Hostx64\x64\cl.exe" /nologo /O2 /MT /EHsc /std:c++17 "/I$root\.local\minhook\include" "$root\native\portraits\image_test.cpp" loader.obj forge-lua.lib buffer.obj hook.obj trampoline.obj hde64.obj /Fe:image_test.exe /link user32.lib gdi32.lib
    if($LASTEXITCODE -ne 0){throw 'Image tests compilation failed'}
    & .\image_test.exe
    if($LASTEXITCODE -ne 0){throw 'Image tests failed'}
    & "$msvc\bin\Hostx64\x64\cl.exe" /nologo /LD /O2 /MT /EHsc /std:c++17 "$root\modkit\examples\native\forge_native\main.cpp" /link /Brepro /OUT:forge_native.dll
    if($LASTEXITCODE -ne 0){throw 'Native example build failed'}
    & "$msvc\bin\Hostx64\x64\cl.exe" /nologo /O2 /MT /EHsc /std:c++17 "/I$root\.local\loader-deps" "$root\native\loader\loader_test.cpp" loader.obj forge-lua.lib /Fe:loader_test.exe
    if($LASTEXITCODE -ne 0){throw 'Loader test compilation failed'}
    & .\loader_test.exe $root
    if($LASTEXITCODE -ne 0){throw 'Loader execution tests failed'}
} finally {Pop-Location}
