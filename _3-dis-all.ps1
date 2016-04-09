param([string]$RootDir = '.')
$VerbosePreference='Continue'

$Python = "C:\Python34\python.exe"

Write-Host "Processing matching files in: $RootDir" -foregroundcolor cyan

Get-ChildItem -Path $RootDir\* -Include Scenario[0-9][0-9][0-9][0-9] | % {
  Write-Verbose $_.name
  & $Python bgidis.py $_.Fullname
}
