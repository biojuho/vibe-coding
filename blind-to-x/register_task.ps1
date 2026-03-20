$action = New-ScheduledTaskAction -Execute "C:\Users\박주호\Desktop\Vibe coding\blind-to-x\run_pipeline.bat"
$trigger = New-ScheduledTaskTrigger -Once -At "06:00" -RepetitionInterval (New-TimeSpan -Hours 3) -RepetitionDuration (New-TimeSpan -Days 365)
Register-ScheduledTask -TaskName "BlindToX_Pipeline" -Action $action -Trigger $trigger -Description "Blind-to-X pipeline (3h interval)" -Force
