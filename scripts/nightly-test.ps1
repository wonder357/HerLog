#Requires -Version 5.1
<#
.SYNOPSIS
    夜间测试运行器：静态检查、后端测试、前端构建、容器编排配置校验，并归档报告。

.DESCRIPTION
    由 Windows 计划任务在夜间调用，也可手动执行。
    - 每个步骤独立计时、独立记录退出码与日志，单步失败不影响后续步骤。
    - 项目缺少某一部分（后端/前端仓库、docker）时该步记为 SKIP，不算失败。
    - 只要有一步 FAIL，整体退出码为 1，计划任务的“上次结果”即可反映失败。
    - 报告写入 artifacts\nightly\<时间戳>\，并更新 artifacts\nightly\latest-summary.json；
      失败时额外写 artifacts\nightly\ALERT.txt，成功后自动清除。
    - 同一时刻只允许一个实例运行；超过 RetainDays 的报告目录自动清理。

.PARAMETER ProjectRoot
    项目根目录，默认是本脚本所在目录的上一级。

.PARAMETER ApiPath
    后端仓库路径。省略时依次查找 <ProjectRoot>\api、%USERPROFILE%\herlog-contest\api。

.PARAMETER ClientPath
    前端仓库路径。省略时依次查找 <ProjectRoot>\client、frontend、web、
    %USERPROFILE%\herlog-contest\client。

.PARAMETER ReportRoot
    报告根目录，默认 <ProjectRoot>\artifacts\nightly。

.PARAMETER PythonPath
    指定 Python 解释器。省略时依次使用 <api>\.venv、<ProjectRoot>\.tools\python、PATH 中的 python。

.PARAMETER NpmPath
    指定 npm.cmd。省略时依次使用 <ProjectRoot>\.tools\node\npm.cmd、PATH 中的 npm.cmd。

.PARAMETER RetainDays
    报告保留天数，默认 14。

.PARAMETER TimeoutMinutes
    单条外部命令的超时分钟数，默认 25。

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\nightly-test.ps1

.EXAMPLE
    .\scripts\nightly-test.ps1 -ApiPath D:\work\api -ClientPath D:\work\client -SkipInfra
#>
[CmdletBinding()]
param(
    [string]$ProjectRoot,
    [string]$ApiPath,
    [string]$ClientPath,
    [string]$ReportRoot,
    [string]$PythonPath,
    [string]$NpmPath,
    [int]$RetainDays = 14,
    [int]$TimeoutMinutes = 25,
    [switch]$SkipStatic,
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$SkipInfra
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

if (-not $ProjectRoot) {
    $scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $PSCommandPath }
    $ProjectRoot = Split-Path -Parent $scriptDir
}
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
if (-not $ReportRoot) { $ReportRoot = Join-Path $ProjectRoot 'artifacts\nightly' }
$ReportRoot = [System.IO.Path]::GetFullPath($ReportRoot)

$RunId = Get-Date -Format 'yyyyMMdd-HHmmss'
$RunDir = Join-Path $ReportRoot $RunId
$RunLog = Join-Path $RunDir 'runner.log'
$StartedAt = Get-Date
$Results = New-Object System.Collections.ArrayList

$mutex = New-Object System.Threading.Mutex($false, 'Herlog-Nightly-Test-Runner')
$acquired = $false
try { $acquired = $mutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $acquired = $true }
if (-not $acquired) {
    Write-Output '[SKIP] 已有一个夜间测试实例在运行，本次退出。'
    exit 0
}

function Write-Log {
    param([string]$Text)
    $line = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $Text
    Write-Host $line
    if ($script:LogWriter) {
        try { $script:LogWriter.WriteLine($line) } catch { }
    }
}

function Initialize-RunLog {
    $encoder = New-Object System.Text.UTF8Encoding($false)
    for ($i = 0; $i -lt 3; $i++) {
        try {
            $writer = New-Object System.IO.StreamWriter($RunLog, $true, $encoder)
            $writer.AutoFlush = $true
            $script:LogWriter = $writer
            return
        }
        catch {
            Start-Sleep -Milliseconds 300
        }
    }
}

function Close-RunLog {
    if ($script:LogWriter) {
        try { $script:LogWriter.Dispose() } catch { }
        $script:LogWriter = $null
    }
}

function Add-Result {
    param(
        [string]$Step,
        [string]$Status,
        [string]$Detail = '',
        [string]$Command = '',
        [double]$Seconds = 0,
        [int]$ExitCode = 0,
        [string]$LogFile = ''
    )
    [void]$Results.Add([pscustomobject]@{
            Step     = $Step
            Status   = $Status
            Detail   = $Detail
            Command  = $Command
            Seconds  = $Seconds
            ExitCode = $ExitCode
            LogFile  = $LogFile
        })
    Write-Log ('[{0}] {1}{2}' -f $Status, $Step, $(if ($Detail) { ' — ' + $Detail } else { '' }))
}

function Get-Tail {
    param([string]$Path, [int]$Lines = 6)
    if (-not ($Path -and (Test-Path -LiteralPath $Path))) { return '' }
    $text = @(Get-Content -LiteralPath $Path -Tail $Lines -Encoding UTF8 -ErrorAction SilentlyContinue) -join ' / '
    if ($text.Length -gt 400) { $text = $text.Substring($text.Length - 400) }
    return $text
}

function Invoke-Tool {
    param(
        [string]$FilePath,
        [string]$Arguments,
        [string]$WorkingDirectory,
        [string]$LogBase,
        [string]$PathPrefix,
        [int]$TimeoutSeconds = ($TimeoutMinutes * 60)
    )
    $outFile = "$LogBase.out.log"
    $errFile = "$LogBase.err.log"
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    if ($FilePath -match '\.(cmd|bat)$') {
        $psi.FileName = $env:ComSpec
        $psi.Arguments = '/d /s /c ""{0}" {1}"' -f $FilePath, $Arguments
    }
    else {
        $psi.FileName = $FilePath
        $psi.Arguments = $Arguments
    }
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    $psi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'
    $psi.EnvironmentVariables['PYTHONUTF8'] = '1'
    if ($PathPrefix) {
        $psi.EnvironmentVariables['PATH'] = $PathPrefix + ';' + [Environment]::GetEnvironmentVariable('PATH')
    }

    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    [void]$process.Start()
    $stdOut = $process.StandardOutput.ReadToEndAsync()
    $stdErr = $process.StandardError.ReadToEndAsync()
    $timedOut = -not $process.WaitForExit($TimeoutSeconds * 1000)
    if ($timedOut) {
        try { $process.Kill() } catch { }
    }
    $process.WaitForExit()
    $watch.Stop()
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($outFile, $stdOut.Result, $utf8)
    [System.IO.File]::WriteAllText($errFile, $stdErr.Result, $utf8)
    $code = if ($timedOut) { -1 } else { $process.ExitCode }
    $process.Dispose()
    return [pscustomobject]@{
        ExitCode = $code
        TimedOut = $timedOut
        Seconds  = [math]::Round($watch.Elapsed.TotalSeconds, 1)
        StdOut   = $outFile
        StdErr   = $errFile
    }
}

function Test-PythonModule {
    param([string]$Python, [string]$Module)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Python -c "import $Module" *> $null
        return ($LASTEXITCODE -eq 0)
    }
    finally { $ErrorActionPreference = $previous }
}

function Resolve-Repo {
    param([string]$Explicit, [string[]]$Fallbacks, [string[]]$Markers)
    $candidates = @()
    if ($Explicit) { $candidates += $Explicit }
    $candidates += $Fallbacks
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        $root = (Resolve-Path -LiteralPath $candidate).Path
        foreach ($marker in $Markers) {
            if (Test-Path -LiteralPath (Join-Path $root $marker)) { return $root }
        }
    }
    return $null
}

function Invoke-StaticChecks {
    $required = @(
        @{ Name = '产品与技术实施说明'; Pattern = '*产品与技术实施说明*.md' },
        @{ Name = '容器编排文件'; Pattern = 'docs\compose.yaml' },
        @{ Name = 'Alembic 迁移'; Pattern = 'docs\*herlog*.py' }
    )
    $missing = @()
    foreach ($item in $required) {
        $hit = @(Get-ChildItem -Path (Join-Path $ProjectRoot $item.Pattern) -File -ErrorAction SilentlyContinue)
        if ($hit.Count -eq 0) { $missing += $item.Name }
    }
    if ($missing.Count -eq 0) {
        Add-Result -Step '文档与资产完整性' -Status 'PASS' -Detail ('3 项齐备')
    }
    else {
        Add-Result -Step '文档与资产完整性' -Status 'FAIL' -Detail ('缺少: ' + ($missing -join '、'))
    }

    $spec = @(Get-ChildItem -LiteralPath $ProjectRoot -Filter '*产品与技术实施说明*.md' -File -ErrorAction SilentlyContinue)
    if ($spec.Count -gt 0) {
        $raw = Get-Content -LiteralPath $spec[0].FullName -Raw -Encoding UTF8
        $broken = $raw.Contains([string][char]0xFFFD)
        Add-Result -Step '说明文档编码' -Status $(if ($broken) { 'FAIL' } else { 'PASS' }) `
            -Detail $(if ($broken) { 'UTF-8 解码出现替换字符，文档可能被非 UTF-8 覆盖' } else { "$($spec[0].Name) 可正常 UTF-8 解码" })
    }

    $secretNames = @('infra.env', '.env', '.env.contest', '.env.production.local')
    $leaked = @()
    foreach ($dir in @($ProjectRoot, (Join-Path $ProjectRoot 'docs'))) {
        if (-not (Test-Path -LiteralPath $dir)) { continue }
        foreach ($name in $secretNames) {
            if (Test-Path -LiteralPath (Join-Path $dir $name)) { $leaked += $name }
        }
        $leaked += @(Get-ChildItem -LiteralPath $dir -File -Filter '*.bundle' -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
    }
    Add-Result -Step '敏感文件落盘' -Status $(if ($leaked.Count -eq 0) { 'PASS' } else { 'WARN' }) `
        -Detail $(if ($leaked.Count -eq 0) { '未发现环境文件或 bundle' } else { '发现: ' + ($leaked -join '、') + '（勿提交）' })

    $git = Get-Command git.exe -ErrorAction SilentlyContinue
    if ($git -and (Test-Path -LiteralPath (Join-Path $ProjectRoot '.git'))) {
        $sha = (& $git.Source -C $ProjectRoot rev-parse --short HEAD 2>$null) -join ''
        $dirty = @(& $git.Source -C $ProjectRoot status --porcelain 2>$null | Where-Object { $_ -notmatch '^(\?\?| M) \.tools/' })
        Add-Result -Step 'Git 工作区' -Status $(if ($dirty.Count -eq 0) { 'PASS' } else { 'WARN' }) `
            -Detail $(if ($dirty.Count -eq 0) { "HEAD $sha，无未提交改动" } else { "HEAD $sha，有 $($dirty.Count) 项未提交改动" })
    }
}

function Invoke-Backend {
    $api = Resolve-Repo -Explicit $ApiPath `
        -Fallbacks @((Join-Path $ProjectRoot 'api'), (Join-Path $ProjectRoot 'backend'), (Join-Path $ProjectRoot 'server'), (Join-Path $env:USERPROFILE 'herlog-contest\api')) `
        -Markers @('pyproject.toml', 'app', 'tests')
    if (-not $api) {
        Add-Result -Step '后端测试' -Status 'SKIP' -Detail '未找到后端仓库（api/），待后端代码就位后自动纳入'
        return
    }

    $python = $null
    if ($PythonPath) {
        if (-not (Test-Path -LiteralPath $PythonPath)) { throw "PythonPath 不存在: $PythonPath" }
        $python = (Resolve-Path -LiteralPath $PythonPath).Path
    }
    else {
        foreach ($candidate in @(
                (Join-Path $api '.venv\Scripts\python.exe'),
                (Join-Path $ProjectRoot '.tools\python\python.exe'))) {
            if (Test-Path -LiteralPath $candidate) { $python = $candidate; break }
        }
        if (-not $python) {
            $found = Get-Command python.exe -ErrorAction SilentlyContinue
            if ($found) { $python = $found.Source }
        }
    }
    if (-not $python) {
        Add-Result -Step '后端测试' -Status 'SKIP' -Detail "找到后端仓库 $api，但未找到 Python 解释器"
        return
    }
    Write-Log "后端仓库: $api / Python: $python"
    $pythonDir = Split-Path -Parent $python

    $target = if (Test-Path -LiteralPath (Join-Path $api 'app')) { Join-Path $api 'app' } else { $api }
    $r = Invoke-Tool -FilePath $python -Arguments ('-m compileall -q "{0}"' -f $target) `
        -WorkingDirectory $api -LogBase (Join-Path $RunDir 'backend-compile') -PathPrefix $pythonDir
    $detail = if ($r.ExitCode -eq 0) { '语法编译通过' } else { Get-Tail $r.StdErr }
    Add-Result -Step '后端语法编译' -Status $(if ($r.ExitCode -eq 0) { 'PASS' } else { 'FAIL' }) `
        -Detail $detail -Command 'python -m compileall' -Seconds $r.Seconds -ExitCode $r.ExitCode `
        -LogFile $r.StdErr

    $hasTests = (Test-Path -LiteralPath (Join-Path $api 'tests')) -or
    (@(Get-ChildItem -LiteralPath $api -Recurse -File -Filter 'test_*.py' -ErrorAction SilentlyContinue).Count -gt 0)
    if ($hasTests) {
        $junit = Join-Path $RunDir 'backend-junit.xml'
        $pytestArgs = '-m pytest -q -p no:cacheprovider --junitxml="{0}"' -f $junit
        if (Test-PythonModule -Python $python -Module 'pytest_cov') {
            $pytestArgs += ' --cov=app --cov-report=term-missing --cov-report=xml:"{0}"' -f (Join-Path $RunDir 'backend-coverage.xml')
        }
        $r = Invoke-Tool -FilePath $python -Arguments $pytestArgs -WorkingDirectory $api `
            -LogBase (Join-Path $RunDir 'backend-pytest') -PathPrefix $pythonDir
        if ($r.TimedOut) {
            Add-Result -Step '后端单元测试' -Status 'FAIL' -Detail "超时（> $TimeoutMinutes 分钟）" `
                -Command 'python -m pytest' -Seconds $r.Seconds -ExitCode $r.ExitCode -LogFile $r.StdOut
        }
        elseif ($r.ExitCode -eq 0) {
            Add-Result -Step '后端单元测试' -Status 'PASS' -Detail 'pytest 全部通过' `
                -Command 'python -m pytest' -Seconds $r.Seconds -ExitCode 0 -LogFile $r.StdOut
        }
        elseif ($r.ExitCode -eq 5) {
            Add-Result -Step '后端单元测试' -Status 'SKIP' -Detail '存在测试目录但未收集到用例' `
                -Command 'python -m pytest' -Seconds $r.Seconds -ExitCode 5 -LogFile $r.StdOut
        }
        else {
            Add-Result -Step '后端单元测试' -Status 'FAIL' -Detail (Get-Tail $r.StdOut) `
                -Command 'python -m pytest' -Seconds $r.Seconds -ExitCode $r.ExitCode -LogFile $r.StdOut
        }
    }
    else {
        Add-Result -Step '后端单元测试' -Status 'SKIP' -Detail '仓库内暂无测试用例'
    }

    if (Test-PythonModule -Python $python -Module 'ruff') {
        $r = Invoke-Tool -FilePath $python -Arguments '-m ruff check .' -WorkingDirectory $api `
            -LogBase (Join-Path $RunDir 'backend-ruff') -PathPrefix $pythonDir
        Add-Result -Step '后端静态检查' -Status $(if ($r.ExitCode -eq 0) { 'PASS' } else { 'FAIL' }) `
            -Detail $(if ($r.ExitCode -eq 0) { 'ruff 无问题' } else { Get-Tail $r.StdOut }) `
            -Command 'python -m ruff check .' -Seconds $r.Seconds -ExitCode $r.ExitCode -LogFile $r.StdOut
    }
    else {
        Add-Result -Step '后端静态检查' -Status 'SKIP' -Detail '未安装 ruff'
    }

    if (Test-Path -LiteralPath (Join-Path $api 'alembic.ini')) {
        $r = Invoke-Tool -FilePath $python -Arguments '-m alembic heads' -WorkingDirectory $api `
            -LogBase (Join-Path $RunDir 'backend-alembic') -PathPrefix $pythonDir
        $heads = @(Get-Content -LiteralPath $r.StdOut -Encoding UTF8 -ErrorAction SilentlyContinue | Where-Object { $_ -match '\(head\)' }) -join '; '
        if ($r.ExitCode -eq 0) {
            Add-Result -Step '迁移脚本可加载' -Status 'PASS' -Detail "heads: $heads" `
                -Command 'python -m alembic heads' -Seconds $r.Seconds -ExitCode 0 -LogFile $r.StdOut
        }
        else {
            Add-Result -Step '迁移脚本可加载' -Status 'WARN' -Detail ('需要 .env.contest 或数据库连接: ' + (Get-Tail $r.StdErr)) `
                -Command 'python -m alembic heads' -Seconds $r.Seconds -ExitCode $r.ExitCode -LogFile $r.StdErr
        }
    }
}

function Invoke-Frontend {
    $client = Resolve-Repo -Explicit $ClientPath `
        -Fallbacks @(
        (Join-Path $ProjectRoot 'client'),
        (Join-Path $ProjectRoot 'frontend'),
        (Join-Path $ProjectRoot 'web'),
        (Join-Path $ProjectRoot 'h5'),
        (Join-Path $env:USERPROFILE 'herlog-contest\client')) `
        -Markers @('package.json')
    if (-not $client) {
        Add-Result -Step '前端构建' -Status 'SKIP' -Detail '未找到前端仓库（client/），待前端代码就位后自动纳入'
        return
    }

    $npm = $null
    if ($NpmPath) {
        if (-not (Test-Path -LiteralPath $NpmPath)) { throw "NpmPath 不存在: $NpmPath" }
        $npm = (Resolve-Path -LiteralPath $NpmPath).Path
    }
    else {
        $bundled = Join-Path $ProjectRoot '.tools\node\npm.cmd'
        if (Test-Path -LiteralPath $bundled) { $npm = $bundled }
        else {
            $found = Get-Command npm.cmd -ErrorAction SilentlyContinue
            if ($found) { $npm = $found.Source }
        }
    }
    if (-not $npm) {
        Add-Result -Step '前端构建' -Status 'SKIP' -Detail "找到前端仓库 $client，但未找到 npm.cmd"
        return
    }
    Write-Log "前端仓库: $client / npm: $npm"
    $npmDir = Split-Path -Parent $npm

    $pkgPath = Join-Path $client 'package.json'
    try {
        $pkg = Get-Content -LiteralPath $pkgPath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        Add-Result -Step '前端构建' -Status 'FAIL' -Detail "package.json 解析失败: $($_.Exception.Message)"
        return
    }
    $scriptNames = @()
    if ($pkg.scripts) { $scriptNames = @($pkg.scripts.PSObject.Properties.Name) }

    if (-not (Test-Path -LiteralPath (Join-Path $client 'node_modules'))) {
        $installArgs = if (Test-Path -LiteralPath (Join-Path $client 'package-lock.json')) {
            'ci --no-audit --no-fund'
        }
        else { 'install --no-audit --no-fund' }
        $r = Invoke-Tool -FilePath $npm -Arguments $installArgs -WorkingDirectory $client `
            -LogBase (Join-Path $RunDir 'frontend-install') -PathPrefix $npmDir -TimeoutSeconds ([math]::Max($TimeoutMinutes, 30) * 60)
        Add-Result -Step '前端依赖安装' -Status $(if ($r.ExitCode -eq 0) { 'PASS' } else { 'FAIL' }) `
            -Detail $(if ($r.ExitCode -eq 0) { "npm $installArgs 完成" } else { Get-Tail $r.StdErr }) `
            -Command "npm $installArgs" -Seconds $r.Seconds -ExitCode $r.ExitCode -LogFile $r.StdErr
        if ($r.ExitCode -ne 0) { return }
    }

    $plan = @()
    foreach ($name in @('type-check', 'typecheck', 'tsc-check', 'lint')) {
        if ($scriptNames -contains $name) { $plan += $name }
    }
    foreach ($name in @('test:unit', 'test')) {
        if ($scriptNames -contains $name) { $plan += $name }
    }
    foreach ($name in @('build:h5', 'build')) {
        if ($scriptNames -contains $name) { $plan += $name; break }
    }
    if ($plan.Count -eq 0) {
        Add-Result -Step '前端构建' -Status 'SKIP' -Detail 'package.json 中无可执行的检查或构建脚本'
        return
    }

    foreach ($name in $plan) {
        $r = Invoke-Tool -FilePath $npm -Arguments "run $name" -WorkingDirectory $client `
            -LogBase (Join-Path $RunDir ('frontend-' + ($name -replace '[:\\/]', '-'))) -PathPrefix $npmDir
        $status = if ($r.TimedOut) { 'FAIL' } elseif ($r.ExitCode -eq 0) { 'PASS' } else { 'FAIL' }
        $detail = if ($r.TimedOut) { "超时（> $TimeoutMinutes 分钟）" }
        elseif ($r.ExitCode -eq 0) { '通过' }
        else { Get-Tail $r.StdOut }
        Add-Result -Step "前端 npm run $name" -Status $status -Detail $detail `
            -Command "npm run $name" -Seconds $r.Seconds -ExitCode $r.ExitCode -LogFile $r.StdOut
    }

    $h5 = Join-Path $client 'dist\build\h5'
    if (($plan -contains 'build:h5') -and (Test-Path -LiteralPath $h5)) {
        $index = Join-Path $h5 'index.html'
        Add-Result -Step '前端产物校验' -Status $(if (Test-Path -LiteralPath $index) { 'PASS' } else { 'FAIL' }) `
            -Detail $(if (Test-Path -LiteralPath $index) { 'dist\build\h5\index.html 存在' } else { '产物缺少 index.html' })
    }
}

function Invoke-Infra {
    $compose = $null
    foreach ($relative in @('docs\compose.yaml', 'docs\compose.yml', 'compose.yaml', 'compose.yml', 'docker-compose.yml')) {
        $candidate = Join-Path $ProjectRoot $relative
        if (Test-Path -LiteralPath $candidate) { $compose = $candidate; break }
    }
    if (-not $compose) {
        Add-Result -Step '容器编排校验' -Status 'SKIP' -Detail '未找到 compose 文件'
        return
    }

    $docker = Get-Command docker.exe -ErrorAction SilentlyContinue
    if (-not $docker) {
        Add-Result -Step '容器编排校验' -Status 'SKIP' -Detail '本机无 docker，跳过 compose 解析（与实施说明当前基线一致）'
        return
    }
    $probe = Invoke-Tool -FilePath $docker.Source -Arguments 'compose version' -WorkingDirectory $ProjectRoot `
        -LogBase (Join-Path $RunDir 'infra-probe') -TimeoutSeconds 120
    if ($probe.ExitCode -ne 0) {
        Add-Result -Step '容器编排校验' -Status 'SKIP' -Detail 'docker compose 插件不可用'
        return
    }

    $envFile = Join-Path $RunDir 'compose-check.env'
    @('HERLOG_DB_PASSWORD=compose-check', 'HERLOG_DB_ROOT_PASSWORD=compose-check') |
        Set-Content -LiteralPath $envFile -Encoding ASCII
    $r = Invoke-Tool -FilePath $docker.Source `
        -Arguments ('compose -f "{0}" --env-file "{1}" config -q' -f $compose, $envFile) `
        -WorkingDirectory $ProjectRoot -LogBase (Join-Path $RunDir 'infra-compose-config') -TimeoutSeconds 180
    Add-Result -Step '容器编排校验' -Status $(if ($r.ExitCode -eq 0) { 'PASS' } else { 'FAIL' }) `
        -Detail $(if ($r.ExitCode -eq 0) { "$([System.IO.Path]::GetFileName($compose)) 解析通过" } else { Get-Tail $r.StdErr }) `
        -Command 'docker compose config -q' -Seconds $r.Seconds -ExitCode $r.ExitCode -LogFile $r.StdErr
}

function Remove-OldRuns {
    if (-not (Test-Path -LiteralPath $ReportRoot)) { return }
    $limit = (Get-Date).AddDays(-$RetainDays)
    Get-ChildItem -LiteralPath $ReportRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d{8}-\d{6}$' -and $_.LastWriteTime -lt $limit } |
    ForEach-Object {
        try { Remove-Item -LiteralPath $_.FullName -Recurse -Force } catch { Write-Log "清理旧报告失败: $($_.FullName)" }
    }
}

function Save-Text {
    param([string]$Path, [string]$Text, [switch]$Bom)
    $encoding = New-Object System.Text.UTF8Encoding($Bom.IsPresent)
    for ($i = 0; $i -lt 3; $i++) {
        try {
            [System.IO.File]::WriteAllText($Path, $Text, $encoding)
            return
        }
        catch {
            if ($i -eq 2) { throw }
            Start-Sleep -Milliseconds 300
        }
    }
}

try {
    New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
    Initialize-RunLog
    Write-Log "夜间测试开始：$ProjectRoot"
    Write-Log "报告目录：$RunDir"

    if (-not $SkipStatic) { Invoke-StaticChecks }
    if (-not $SkipBackend) { Invoke-Backend }
    if (-not $SkipFrontend) { Invoke-Frontend }
    if (-not $SkipInfra) { Invoke-Infra }
}
catch {
    Add-Result -Step '运行器' -Status 'FAIL' -Detail $_.Exception.Message
}

$FinishedAt = Get-Date
$failed = @($Results | Where-Object { $_.Status -eq 'FAIL' })
$warned = @($Results | Where-Object { $_.Status -eq 'WARN' })
$passed = @($Results | Where-Object { $_.Status -eq 'PASS' })
$skipped = @($Results | Where-Object { $_.Status -eq 'SKIP' })
$overall = if ($failed.Count -gt 0) { 'FAIL' } else { 'PASS' }

$summary = [ordered]@{
    runId         = $RunId
    projectRoot   = $ProjectRoot
    machine       = $env:COMPUTERNAME
    user          = $env:USERNAME
    startedAt     = $StartedAt.ToString('s')
    finishedAt    = $FinishedAt.ToString('s')
    durationSec   = [math]::Round(($FinishedAt - $StartedAt).TotalSeconds, 1)
    status        = $overall
    counts        = [ordered]@{ pass = $passed.Count; fail = $failed.Count; warn = $warned.Count; skip = $skipped.Count }
    powershell    = $PSVersionTable.PSVersion.ToString()
    gitHead       = $(if (Test-Path -LiteralPath (Join-Path $ProjectRoot '.git')) { (@(& git -C $ProjectRoot rev-parse --short HEAD 2>$null) -join '') } else { '' })
    steps         = @($Results)
}
$jsonPath = Join-Path $RunDir 'summary.json'
Save-Text -Path $jsonPath -Text ($summary | ConvertTo-Json -Depth 6)

$md = New-Object System.Text.StringBuilder
[void]$md.AppendLine("# 夜间测试报告 $RunId")
[void]$md.AppendLine('')
[void]$md.AppendLine("- 结论：**$overall**（通过 $($passed.Count) / 失败 $($failed.Count) / 警告 $($warned.Count) / 跳过 $($skipped.Count)）")
[void]$md.AppendLine("- 开始：$($StartedAt.ToString('yyyy-MM-dd HH:mm:ss'))　耗时：$($summary.durationSec) 秒　主机：$($summary.machine)")
[void]$md.AppendLine("- 项目：$ProjectRoot")
[void]$md.AppendLine('')
[void]$md.AppendLine('| 步骤 | 结果 | 耗时(s) | 说明 |')
[void]$md.AppendLine('|---|---|---|---|')
foreach ($item in $Results) {
    $cell = ($item.Detail -replace '\|', '\|' -replace "`r?`n", ' ')
    [void]$md.AppendLine(('| {0} | {1} | {2} | {3} |' -f $item.Step, $item.Status, $item.Seconds, $cell))
}
Save-Text -Path (Join-Path $RunDir 'report.md') -Text $md.ToString() -Bom

New-Item -ItemType Directory -Force -Path $ReportRoot | Out-Null
Save-Text -Path (Join-Path $ReportRoot 'latest-summary.json') -Text ($summary | ConvertTo-Json -Depth 6)
$alertPath = Join-Path $ReportRoot 'ALERT.txt'
if ($failed.Count -gt 0) {
    $alert = @(
        "夜间测试失败：$RunId",
        "主机：$($summary.machine)　项目：$ProjectRoot",
        ''
    ) + @($failed | ForEach-Object { "- [$($_.Step)] $($_.Detail)（退出码 $($_.ExitCode)，日志 $($_.LogFile)）" }) +
    @('', "完整报告：$RunDir")
    Save-Text -Path $alertPath -Text ($alert -join "`r`n") -Bom
}
elseif (Test-Path -LiteralPath $alertPath) {
    Remove-Item -LiteralPath $alertPath -Force
}

Remove-OldRuns

Write-Log ('结论: {0}（通过 {1} / 失败 {2} / 警告 {3} / 跳过 {4}），报告: {5}' -f $overall, $passed.Count, $failed.Count, $warned.Count, $skipped.Count, $RunDir)
Close-RunLog
$mutex.ReleaseMutex()
if ($failed.Count -gt 0) { exit 1 }
exit 0
