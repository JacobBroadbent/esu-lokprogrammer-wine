$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$lock = Get-Content (Join-Path $root 'dependencies.json') -Raw | ConvertFrom-Json
$cache = Join-Path $root '.cache'
$outDir = Join-Path $root 'build'
New-Item -ItemType Directory -Force $cache, $outDir | Out-Null
$package = Join-Path $cache 'lib.harmony.2.3.3.nupkg'
if (!(Test-Path $package) -or (Get-FileHash $package -Algorithm SHA256).Hash.ToLowerInvariant() -ne $lock.harmony.sha256) {
    Invoke-WebRequest $lock.harmony.url -OutFile $package
}
if ((Get-FileHash $package -Algorithm SHA256).Hash.ToLowerInvariant() -ne $lock.harmony.sha256) {
    throw 'Harmony package SHA-256 mismatch'
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($package)
try {
    foreach ($item in @(@('lib/net472/0Harmony.dll', '0Harmony.dll'), @('LICENSE', 'Harmony-LICENSE.txt'))) {
        $entry = $zip.GetEntry($item[0])
        if ($null -eq $entry) { throw "Missing NuGet member $($item[0])" }
        [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, (Join-Path $outDir $item[1]), $true)
    }
} finally { $zip.Dispose() }
$compiler = Join-Path $env:WINDIR 'Microsoft.NET/Framework/v4.0.30319/csc.exe'
if (!(Test-Path $compiler)) { throw '.NET Framework compiler not found' }
$target = Join-Path $outDir 'LokProgrammerWineCompat.exe'
$sources = @('LokProgrammerWineCompat.cs', 'WmiDirectScopeCheck.cs', 'SerialTimeoutCompat.cs') |
    ForEach-Object { Join-Path $root "src/$_" }
& $compiler /nologo /platform:x86 /reference:System.Management.dll "/reference:$(Join-Path $outDir '0Harmony.dll')" "/out:$target" /main:LokProgrammerWineCompat @sources
if ($LASTEXITCODE -ne 0) { throw 'C# compilation failed' }
$lines = Get-ChildItem $outDir -File | Where-Object Name -ne 'SHA256SUMS' | Sort-Object Name | ForEach-Object {
    "$((Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant())  $($_.Name)"
}
$lines | Set-Content (Join-Path $outDir 'SHA256SUMS') -Encoding ASCII
Write-Output "Built $target"
