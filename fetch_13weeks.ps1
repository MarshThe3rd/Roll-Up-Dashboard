# TPA 13-week chunked fetch + combine  (sequential, proven cmd approach)
# Each fiscal week queried one at a time, results appended into one CSV.

$env:CLOUDSDK_PYTHON = "C:\Users\m0m0ag5\.code-puppy-venv\Scripts\python.exe"
$BASE   = "C:\Users\m0m0ag5\Documents\puppy_workspace\Roll_up_dashboard"
$PROJ   = "wmt-sc-ops-sandbox"
$OUTCSV = "$BASE\tpa_associate_performance_13weeks.csv"

# Write SQL without UTF-8 BOM so bq CLI reads it cleanly
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

$TMPL = @'
WITH dept_goals AS (
  SELECT SC_CODE_ID, FC_ID, GOAL, GOAL_UOM, ACTIVE_DATE, INACTIVE_DATE
  FROM `wmt-drax-prod.DRAX_VM.INPUTS_DEPARTMENTGOAL`
  WHERE FC_ID = 'TPA'
)
SELECT
  p.DEFAULT_ID        AS default_id,
  p.FC_ID,
  p.DATE              AS date,
  CASE WHEN p.DATE >= DATE '2026-01-31' THEN 2027 ELSE 2026 END AS WM_FISCAL_YEAR,
  CASE
    WHEN p.DATE >= DATE '2026-01-31'
      THEN DIV(DATE_DIFF(p.DATE, DATE '2026-01-31', DAY), 7) + 1
    ELSE DIV(DATE_DIFF(p.DATE, DATE '2025-02-01', DAY), 7) + 1
  END AS WM_FISCAL_WEEK,
  CASE
    WHEN p.DATE >= DATE '2026-01-31'
      THEN DATE_ADD(DATE '2026-01-31',
             INTERVAL (DIV(DATE_DIFF(p.DATE, DATE '2026-01-31', DAY), 7) * 7) DAY)
    ELSE DATE_ADD(DATE '2025-02-01',
             INTERVAL (DIV(DATE_DIFF(p.DATE, DATE '2025-02-01', DAY), 7) * 7) DAY)
  END AS WM_FISCAL_WEEK_START,
  p.SC_CODE_ID,
  p.HOME_CODE_ID,
  p.AREA,
  p.SUPER_DEPARTMENT,
  p.DEPARTMENT,
  p.HOURS,
  p.IDLE_HOURS,
  p.VOLUME,
  dg.GOAL,
  dg.GOAL_UOM,
  SAFE_DIVIDE(p.VOLUME, p.HOURS)                              AS RATE_PER_HOUR,
  SAFE_DIVIDE(SAFE_DIVIDE(p.VOLUME, p.HOURS), dg.GOAL) * 100  AS PCT_TO_GOAL
FROM `wmt-drax-prod.DRAX_VM.VIEWS_ASSOCIATE_PERFORMANCE_DAY` p
LEFT JOIN dept_goals dg
  ON p.SC_CODE_ID = dg.SC_CODE_ID
  AND p.DATE >= dg.ACTIVE_DATE
  AND (dg.INACTIVE_DATE IS NULL OR p.DATE < dg.INACTIVE_DATE)
WHERE p.FC_ID = 'TPA'
  AND p.HOURS > 0
  AND p.DATE BETWEEN DATE '__S__' AND DATE '__E__'
ORDER BY p.DATE, p.DEFAULT_ID, p.SC_CODE_ID
'@

$chunks = @(
    @{L="A"; S="2025-12-27"; E="2026-01-02"; F="FY2026-W48"},
    @{L="B"; S="2026-01-03"; E="2026-01-09"; F="FY2026-W49"},
    @{L="C"; S="2026-01-10"; E="2026-01-16"; F="FY2026-W50"},
    @{L="D"; S="2026-01-17"; E="2026-01-23"; F="FY2026-W51"},
    @{L="E"; S="2026-01-24"; E="2026-01-30"; F="FY2026-W52"},
    @{L="F"; S="2026-01-31"; E="2026-02-06"; F="FY2027-W01"},
    @{L="G"; S="2026-02-07"; E="2026-02-13"; F="FY2027-W02"},
    @{L="H"; S="2026-02-14"; E="2026-02-20"; F="FY2027-W03"},
    @{L="I"; S="2026-02-21"; E="2026-02-27"; F="FY2027-W04"},
    @{L="J"; S="2026-02-28"; E="2026-03-06"; F="FY2027-W05"},
    @{L="K"; S="2026-03-07"; E="2026-03-13"; F="FY2027-W06"},
    @{L="L"; S="2026-03-14"; E="2026-03-20"; F="FY2027-W07"},
    @{L="M"; S="2026-03-21"; E="2026-03-27"; F="FY2027-W08"}
)

# Delete any stale output file before starting
Remove-Item $OUTCSV -ErrorAction SilentlyContinue

$isFirst   = $true
$totalRows = 0
$summary   = @()
$sqlFile   = "$BASE\current_chunk.sql"

Write-Host ""
Write-Host "=== TPA 13-Week Chunked Query ==="
Write-Host ("Output: " + $OUTCSV)
Write-Host ""

foreach ($c in $chunks) {
    $lbl = $c.L
    $sql = $TMPL.Replace('__S__', $c.S).Replace('__E__', $c.E)

    # Write SQL file without BOM
    [System.IO.File]::WriteAllText($sqlFile, $sql, $utf8NoBom)

    Write-Host -NoNewline ("  [" + $lbl + "] " + $c.F + " (" + $c.S + " to " + $c.E + ") ... ")

    # Run via the proven cmd approach
    $out = cmd /c "set CLOUDSDK_PYTHON=C:\Users\m0m0ag5\.code-puppy-venv\Scripts\python.exe && bq query --use_legacy_sql=false --project_id=$PROJ --format=csv --max_rows=5000 < $sqlFile" 2>$null

    if ($null -eq $out -or $out.Count -eq 0) {
        Write-Host "EMPTY / ERROR"
        $summary += [pscustomobject]@{Chunk=$lbl; Fiscal=$c.F; Rows=0; Status="EMPTY"}
        continue
    }

    if ($out[0] -match '^Error') {
        Write-Host ("BQ ERROR: " + $out[0])
        $summary += [pscustomobject]@{Chunk=$lbl; Fiscal=$c.F; Rows="ERR"; Status="ERROR"}
        continue
    }

    $dataRows  = $out.Count - 1    # subtract header line
    $totalRows += $dataRows
    Write-Host ("$dataRows rows")
    $summary += [pscustomobject]@{Chunk=$lbl; Fiscal=$c.F; Rows=$dataRows; Status="OK"}

    if ($isFirst) {
        $out | Out-File -FilePath $OUTCSV -Encoding utf8
        $isFirst = $false
    } else {
        $out | Select-Object -Skip 1 | Out-File -FilePath $OUTCSV -Encoding utf8 -Append
    }
}

# Cleanup temp sql file
Remove-Item $sqlFile -ErrorAction SilentlyContinue
Remove-Item "$BASE\dbg_chunk.sql" -ErrorAction SilentlyContinue
Remove-Item "$BASE\dbg_chunk.csv" -ErrorAction SilentlyContinue
Remove-Item "$BASE\dbg_chunk.err" -ErrorAction SilentlyContinue
Remove-Item "$BASE\debug_chunk.ps1" -ErrorAction SilentlyContinue

$finalLines = (Get-Content $OUTCSV | Measure-Object -Line).Lines

Write-Host ""
Write-Host "========================================"
Write-Host "CHUNK SUMMARY:"
$summary | Format-Table -AutoSize
Write-Host ("TOTAL DATA ROWS : " + $totalRows)
Write-Host ("FINAL FILE LINES: " + $finalLines + "  (incl. 1 header)")
Write-Host ("OUTPUT FILE     : " + $OUTCSV)
Write-Host "========================================"
