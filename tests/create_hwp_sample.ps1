param([Parameter(Mandatory=$true)][string]$OutputPath)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$OutputPath = [IO.Path]::GetFullPath($OutputPath)
$hwp = $null
try {
    $hwp = New-Object -ComObject HWPFrame.HwpObject
    try { $hwp.XHwpWindows.Item(0).Visible = $false } catch {}
    try { $hwp.HAction.Run('FileNew') | Out-Null } catch {}
    $set = $hwp.HParameterSet.HInsertText
    $hwp.HAction.GetDefault('InsertText', $set.HSet)
    $set.Text = "포맷브릿지 HWP 네이티브 검증`r`nHWP에서 PDF로 변환합니다."
    $hwp.HAction.Execute('InsertText', $set.HSet) | Out-Null
    $saved = $hwp.SaveAs($OutputPath, 'HWP', '')
    if (-not $saved) { throw 'HWP 샘플 저장 실패' }
} finally {
    if ($null -ne $hwp) { try { $hwp.Clear(1) } catch {}; try { $hwp.Quit() } catch {} }
    if ($null -ne $hwp) { try { [Runtime.InteropServices.Marshal]::FinalReleaseComObject($hwp) | Out-Null } catch {} }
}
Write-Output "OK: $OutputPath"

