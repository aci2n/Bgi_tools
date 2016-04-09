param([string]$RootDir = 'itsusora')
$VerbosePreference='Continue'

$Python = "C:\Python34\python.exe"

Write-Host "Processing matching files in: $RootDir" -foregroundcolor cyan

Get-ChildItem -Path $RootDir\* -Include Scenario[0-9][0-9][0-9][0-9].bsd | % {
  Write-Verbose $_.name
  & $Python bgias.py $_.Fullname
}
