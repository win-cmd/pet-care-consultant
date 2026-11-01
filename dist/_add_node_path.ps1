$ErrorActionPreference = 'Stop'
$add = 'C:\Program Files\nodejs'
$before = [Environment]::GetEnvironmentVariable('Path', 'User')
Set-Content -Path 'dist\_user_path_backup.txt' -Value $before -Encoding UTF8
Write-Output "BEFORE=[$before]"
$parts = @()
if ($before) { $parts = $before -split ';' | Where-Object { $_ -ne '' } }
if ($parts -contains $add) {
  Write-Output 'RESULT=ALREADY-PRESENT'
} else {
  $parts += $add
  $after = ($parts -join ';')
  [Environment]::SetEnvironmentVariable('Path', $after, 'User')
  Write-Output "AFTER=[$([Environment]::GetEnvironmentVariable('Path','User'))]"
  Write-Output 'RESULT=ADDED'
}
