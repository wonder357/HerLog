#Requires -Version 5.1
<#
.SYNOPSIS
    注册/更新/移除“夜间测试”计划任务。

.DESCRIPTION
    以当前用户身份注册任务，每天固定时间运行 scripts\nightly-test.ps1。
    - 默认 Interactive 登录类型：仅在用户登录时运行，可访问网络与用户级缓存。
    - S4U：未登录也运行，但无权访问网络（npm ci / git 拉取会失败）。
    - Password：未登录也运行且可联网，需交互输入或传入凭据。
    - 错过触发时间后在机器可用时补跑；同一任务多实例策略为 IgnoreNew，避免与
      运行器内置的互斥锁叠加时冲突。
    - 任务脚本自行写日志与报告，计划任务只负责按退出码记录 0（通过）/1（失败）。

.PARAMETER TaskName
    任务名称，默认 Herlog-Nightly-Test。

.PARAMETER At
    每日触发时间（24 小时制 HH:mm），默认 02:30。

.PARAMETER LogonType
    Interactive（默认）、S4U 或 Password。

.PARAMETER Credential
    当 LogonType 为 Password 时使用；省略则交互提示。

.PARAMETER WakeToRun
    到点唤醒休眠中的机器。

.PARAMETER RunNow
    注册后立即运行一次。

.PARAMETER Status
    只查询任务状态，不做修改。

.PARAMETER Unregister
    删除任务。

.EXAMPLE
    .\scripts\register-nightly-test.ps1 -RunNow

.EXAMPLE
    .\scripts\register-nightly-test.ps1 -At 03:15 -LogonType S4U

.EXAMPLE
    .\scripts\register-nightly-test.ps1 -Status
    .\scripts\register-nightly-test.ps1 -Unregister
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$TaskName = 'Herlog-Nightly-Test',
    [string]$At = '02:30',
    [ValidateSet('Interactive', 'S4U', 'Password')]
    [string]$LogonType = 'Interactive',
    [pscredential]$Credential,
    [switch]$WakeToRun,
    [switch]$RunNow,
    [switch]$Status,
    [switch]$Unregister
)

$ErrorActionPreference = 'Stop'
$RunnerPath = Join-Path $PSScriptRoot 'nightly-test.ps1'
$ReportRoot = Join-Path (Split-Path -Parent $PSScriptRoot) 'artifacts\nightly'

function Show-TaskState {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Host "任务 $TaskName 不存在。"
        return $null
    }
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    $trigger = ($task.Triggers | ForEach-Object { $_.StartBoundary }) -join ', '
    Write-Host "任务: $TaskName　状态: $($task.State)"
    Write-Host "触发时间: $trigger　登录类型: $($task.Principal.LogonType)"
    Write-Host ('上次运行: {0}　上次结果: 0x{1:X8}　下次运行: {2}' -f $info.LastRunTime, $info.LastTaskResult, $info.NextRunTime)
    Write-Host "报告目录: $ReportRoot"
    if (Test-Path -LiteralPath (Join-Path $ReportRoot 'latest-summary.json')) {
        $latest = Get-Content -LiteralPath (Join-Path $ReportRoot 'latest-summary.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        Write-Host "最近一次结果: $($latest.status)　运行号: $($latest.runId)　结束: $($latest.finishedAt)"
    }
    return $task
}

if ($Status) {
    [void](Show-TaskState)
    return
}

if ($Unregister) {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Output "任务 $TaskName 不存在，无需删除。"
        return
    }
    if ($PSCmdlet.ShouldProcess($TaskName, '删除计划任务')) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Output "已删除任务 $TaskName。历史报告仍保留在 $ReportRoot。"
    }
    return
}

if (-not (Test-Path -LiteralPath $RunnerPath)) { throw "找不到运行器: $RunnerPath" }

try { $triggerTime = [datetime]::ParseExact($At, 'HH:mm', $null) }
catch { throw "At 需要 24 小时制 HH:mm 格式，收到: $At" }
$action = New-ScheduledTaskAction -Execute (Join-Path $PSHOME 'powershell.exe') `
    -Argument ('-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $RunnerPath) `
    -WorkingDirectory (Split-Path -Parent $PSScriptRoot)
$trigger = New-ScheduledTaskTrigger -Daily -At $triggerTime
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -RestartCount 1 -RestartInterval (New-TimeSpan -Minutes 30) `
    -WakeToRun:$WakeToRun

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing -and -not $PSCmdlet.ShouldProcess($TaskName, '覆盖已有计划任务')) { return }

if ($existing) { Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false }

$description = '每天夜间运行 scripts\nightly-test.ps1：静态检查、后端 pytest、前端构建、compose 校验，结果写入 artifacts\nightly。'
if ($LogonType -eq 'Password') {
    if (-not $Credential) { $Credential = Get-Credential -UserName "$env:USERDOMAIN\$env:USERNAME" -Message '计划任务运行账户' }
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
        -Description $description -User $Credential.UserName `
        -Password $Credential.GetNetworkCredential().Password | Out-Null
}
else {
    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType $LogonType -RunLevel Limited
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
        -Principal $principal -Description $description | Out-Null
}

Write-Output "已注册任务 $TaskName，每天 $At 运行。"
Write-Output "运行器: $RunnerPath"
[void](Show-TaskState)

if ($RunNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output '已触发一次运行，结果见上方“上次结果”与报告目录。'
}
