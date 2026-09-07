param(
  [Parameter(Mandatory=$true)][string]$Log,
  [string]$Label = "run"
)
$ErrorActionPreference = 'Stop'
if (!(Test-Path $Log)) { throw "Log not found: $Log" }
$rx = [regex]'network job\s+\d+\s+done in\s+([0-9]+(?:\.[0-9]+)?)\s*ms'
$vals = [System.Collections.Generic.List[double]]::new()
Get-Content $Log | ForEach-Object {
  $m = $rx.Match($_)
  if ($m.Success) { $vals.Add([double]$m.Groups[1].Value) }
}
if ($vals.Count -lt 5) { throw "Only $($vals.Count) NR timings found; capture a longer run." }
$a = @($vals | Sort-Object)
function Pct([double]$p) {
  $i = [Math]::Min($a.Count-1, [Math]::Max(0, [Math]::Ceiling($p*$a.Count)-1))
  return [double]$a[$i]
}
$mean = ($a | Measure-Object -Average).Average
$median = Pct 0.50
$p95 = Pct 0.95
$p99 = Pct 0.99
$fps = 1000.0 / $median
$out = [pscustomobject]@{
  Label=$Label; Samples=$a.Count; MeanMs=[Math]::Round($mean,2)
  MedianMs=[Math]::Round($median,2); P95Ms=[Math]::Round($p95,2)
  P99Ms=[Math]::Round($p99,2); NrCeilingFps=[Math]::Round($fps,1)
}
$out | Format-List
$out | ConvertTo-Json -Compress