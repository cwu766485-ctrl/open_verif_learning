param(
    [string]$Source = "rtl/Cache.v",
    [string]$OutputDir = "rtl/modular"
)

$sourcePath = (Resolve-Path -LiteralPath $Source).Path
$outputPath = Join-Path (Get-Location) $OutputDir
$text = [System.IO.File]::ReadAllText($sourcePath)
$matches = [regex]::Matches($text, '(?m)^module\s+([A-Za-z0-9_]+)\s*\(')

if ($matches.Count -eq 0) {
    throw "No Verilog modules found in $sourcePath"
}

New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)
$fileNames = New-Object System.Collections.Generic.List[string]

for ($index = 0; $index -lt $matches.Count; $index++) {
    $start = $matches[$index].Index
    $end = if ($index + 1 -lt $matches.Count) { $matches[$index + 1].Index } else { $text.Length }
    $moduleName = $matches[$index].Groups[1].Value
    $fileName = "$moduleName.v"
    [System.IO.File]::WriteAllText((Join-Path $outputPath $fileName), $text.Substring($start, $end - $start), $utf8)
    $fileNames.Add($fileName)
}

[System.IO.File]::WriteAllLines((Join-Path $outputPath "Cache.files.f"), $fileNames, $utf8)
Write-Host ("Split {0} modules from {1} into {2}" -f $matches.Count, $sourcePath, $outputPath)
