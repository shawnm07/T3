# Register Trading Bot scheduled tasks in Windows Task Scheduler.
# Run in an ELEVATED PowerShell: right-click PowerShell -> Run as Administrator.
#
# === Timezone: Phoenix, Arizona (MST, UTC-7 year-round — no DST) ===
# These LOCAL (Phoenix) times are set for US/Eastern EDT (mid-March to early-November).
# When the East Coast switches to EST in November, re-run this script OR manually
# shift each task +1 hour (because Phoenix <-> ET gap changes from 3h to 2h).
#
# Market hours reference:
#   EDT (now):   ET 09:30-16:00 = Phoenix 06:30-13:00
#   EST (Nov-Mar): ET 09:30-16:00 = Phoenix 07:30-14:30
#
# To remove all tasks later:  .\scripts\remove_schedule.ps1

$ErrorActionPreference = "Stop"

$BotDir = "C:\Users\shawn\OneDrive\Documents\Tim\trading-bot"
$Python = Join-Path $BotDir ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Python venv not found at $Python. Run: py -3.11 -m venv .venv"
    exit 1
}

function Register-BotTask {
    param(
        [string]$Name,
        [string]$ScriptPath,
        $Triggers,
        [string[]]$Args = @()
    )
    $taskName = "TradingBot_$Name"
    $argList = @("`"$ScriptPath`"") + $Args
    $action = New-ScheduledTaskAction -Execute $Python -Argument ($argList -join " ") -WorkingDirectory $BotDir
    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -DontStopIfGoingOnBatteries `
        -AllowStartIfOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 60)
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited

    Write-Host "Registering: $taskName"
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $Triggers `
        -Settings $settings `
        -Principal $principal `
        -Force | Out-Null
}

$weekdays = @("Monday","Tuesday","Wednesday","Thursday","Friday")

# Pre-market brief: Phoenix 05:30 (= 08:30 ET EDT), weekdays
$triggerPre = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $weekdays -At "05:30"
Register-BotTask "PreMarket" (Join-Path $BotDir "scripts\premarket_brief.py") @($triggerPre)

# Intraday scans: Phoenix 07:00, 09:00, 11:00, 12:30 (= 10/12/14/15:30 ET EDT), weekdays
foreach ($t in @("07:00","09:00","11:00","12:30")) {
    $trig = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $weekdays -At $t
    $tag = "Scan_" + ($t -replace ":", "")
    Register-BotTask $tag (Join-Path $BotDir "scripts\scan_and_trade.py") @($trig)
}

# Pre-close overnight decision: Phoenix 12:55 (= 15:55 ET EDT, 5 min before close), weekdays
$triggerPreClose = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $weekdays -At "12:55"
Register-BotTask "PreClose" (Join-Path $BotDir "scripts\preclose_decision.py") @($triggerPreClose)

# EOD report: Phoenix 13:15 (= 16:15 ET EDT), weekdays
$triggerEod = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek $weekdays -At "13:15"
Register-BotTask "EOD" (Join-Path $BotDir "scripts\eod_report.py") @($triggerEod)

# Weekly review: Friday Phoenix 14:00 (= 17:00 ET EDT)
$triggerWeek = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Friday -At "14:00"
Register-BotTask "WeeklyReview" (Join-Path $BotDir "scripts\weekly_review.py") @($triggerWeek)

# Crypto: every 4 hours, 24/7 (crypto trades nonstop)
$cryptoStart = Get-Date "00:05"
$triggerCrypto = New-ScheduledTaskTrigger -Once -At $cryptoStart `
    -RepetitionInterval (New-TimeSpan -Hours 4) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
Register-BotTask "Crypto" (Join-Path $BotDir "scripts\crypto_check.py") @($triggerCrypto)

# Post-mortem Telegram bridge: every 30 min, 24/7. Polls GitHub for new
# postmortem-YYYY-MM-DD branches created by the remote agent and sends a
# Telegram summary. Also polls Telegram for 'accept/reject postmortem-...'
# replies and merges or deletes the branch accordingly.
$bridgeStart = Get-Date "00:20"
$triggerBridge = New-ScheduledTaskTrigger -Once -At $bridgeStart `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
Register-BotTask "PostmortemBridge" (Join-Path $BotDir "scripts\telegram_postmortem_bridge.py") @($triggerBridge)

Write-Host ""
Write-Host "=== Registered Tasks ===" -ForegroundColor Green
Get-ScheduledTask | Where-Object { $_.TaskName -like "TradingBot_*" } |
    Select-Object TaskName, State, @{Name="NextRun";Expression={(Get-ScheduledTaskInfo $_).NextRunTime}} |
    Format-Table -AutoSize

Write-Host ""
Write-Host "Tip: to trigger a task immediately for testing:" -ForegroundColor Yellow
Write-Host '  Start-ScheduledTask -TaskName "TradingBot_Scan_1000"' -ForegroundColor Yellow
