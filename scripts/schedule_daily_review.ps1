# Registers a Windows Task Scheduler task to run daily_review.py
# at 5:00 PM Monday-Friday (America/Phoenix — no DST, always UTC-7).
# Run once as Administrator:  .\scripts\schedule_daily_review.ps1

$TaskName  = "TradingBot-DailyReview"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
$Python    = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Script    = Join-Path $ScriptDir "daily_review.py"
$LogFile   = Join-Path $RepoRoot "data\logs\daily_review.log"

# Remove existing task if present
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$Action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "`"$Script`"" `
    -WorkingDirectory $RepoRoot

# 5 pm Mon-Fri; append stdout/stderr to log
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -DontStopOnIdleEnd

$Trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday `
    -At "17:00"

Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $Action `
    -Trigger   $Trigger `
    -Settings  $Settings `
    -RunLevel  Highest `
    -Force | Out-Null

Write-Host "Task '$TaskName' registered — runs Mon-Fri at 5:00 PM."
Write-Host "Output goes to: $LogFile"
Write-Host "To run immediately: Start-ScheduledTask -TaskName '$TaskName'"
