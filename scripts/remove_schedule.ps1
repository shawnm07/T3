# Remove all TradingBot_* scheduled tasks. Run in elevated PowerShell.
Get-ScheduledTask | Where-Object { $_.TaskName -like "TradingBot_*" } | ForEach-Object {
    Write-Host "Removing $($_.TaskName)"
    Unregister-ScheduledTask -TaskName $_.TaskName -Confirm:$false
}
Write-Host "Done." -ForegroundColor Green
