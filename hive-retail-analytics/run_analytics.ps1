# =============================================================================
# run_analytics.ps1
#
# Executes every HiveQL analytics script against the running HiveServer2 and
# saves each result set as a machine-readable TSV file under outputs/.
#
# Prerequisites:
#   * HiveServer2 running (docker compose up -d) on localhost:10000
#   * Schema + data already loaded (run 01..04 scripts first)
#   * Processed CSV copied into the container at /tmp/online_retail_clean.csv
#
# Usage (PowerShell, from the project root):
#   .\run_analytics.ps1
#
# beeline exits with code 1 because of a harmless "Failed to create directory:
# /home/hive/.beeline" warning; the result set is still emitted on stdout, so we
# capture stdout and filter out log noise.
# =============================================================================
$ErrorActionPreference = "Continue"

$container = "hive-server"
$jdbc      = "jdbc:hive2://localhost:10000"
$scriptDir = "/tmp/hive-scripts"
$outDir    = Join-Path $PSScriptRoot "outputs"
if (!(Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

$scripts = @(
    "a_dataset_overview.hql",
    "b_monthly_sales.hql",
    "c_product_quantity_all.hql",
    "c_product_top20_quantity.hql",
    "c_product_top20_revenue.hql",
    "c_product_low_volume.hql",
    "d_category_analysis.hql",
    "e_country_summary.hql",
    "e_country_monthly.hql",
    "f_cancellation_summary.hql",
    "f_quantity_direction.hql",
    "f_revenue_effect.hql",
    "f_cancellation_by_country.hql",
    "g_daily_trend.hql",
    "g_weekday_weekend.hql",
    "g_hourly_pattern.hql",
    "g_avg_transaction_value.hql",
    "g_customer_txn_distribution.hql",
    "g_repeat_activity.hql"
)

function Filter-BeineleOutput {
    param([string]$path)
    $content = Get-Content -Path $path
    $keep = $content | Where-Object {
        $_ -ne $null -and
        $_ -notmatch "SLF4J" -and
        $_ -notmatch "^\[WARN\]" -and
        $_ -notmatch "^\[INFO\]" -and
        $_ -notmatch "Connecting to jdbc" -and
        $_ -notmatch "No such file or directory" -and
        $_ -notmatch "File file:.*does not exist" -and
        $_ -notmatch "^\d{2}/\d{2}/\d{2}" -and
        $_.Trim() -ne ""
    }
    $keep | Set-Content -Path $path -Encoding utf8
}

$results = @()
foreach ($s in $scripts) {
    $outName = [System.IO.Path]::GetFileNameWithoutExtension($s) + ".tsv"
    $outPath = Join-Path $outDir $outName
    $rawPath = Join-Path $outDir (".raw_" + $outName)

    Write-Host "Running $s ..."
    # Invoke via cmd.exe so PowerShell redirection behaves cleanly
    & cmd /c "docker exec $container beeline -u jdbc:hive2://localhost:10000 --silent=true --showHeader=true --outputformat=tsv2 -f $scriptDir/$s 2> nul" > $rawPath

    if (Test-Path $rawPath) {
        Filter-BeineleOutput -path $rawPath
        Move-Item -Path $rawPath -Destination $outPath -Force
        $lines = (Get-Content -Path $outPath).Count
        Write-Host "  -> $outPath ($lines lines)"
        $results += [pscustomobject]@{ Script = $s; Output = $outPath; Lines = $lines; Status = "OK" }
    } else {
        Write-Host "  !! NO OUTPUT for $s" -ForegroundColor Yellow
        $results += [pscustomobject]@{ Script = $s; Output = $null; Lines = 0; Status = "NO_OUTPUT" }
    }
}

Write-Host "`n=== Analytics execution complete ==="
$results | Format-Table -AutoSize
