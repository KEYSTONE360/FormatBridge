param(
    [Parameter(Mandatory=$true)][ValidateSet('word','excel','powerpoint','hwp')][string]$Engine,
    [Parameter(Mandatory=$true)][string]$InputPath,
    [Parameter(Mandatory=$true)][string]$OutputPath,
    [Parameter(Mandatory=$true)][string]$TargetExt
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$InputPath = [IO.Path]::GetFullPath($InputPath)
$OutputPath = [IO.Path]::GetFullPath($OutputPath)
$TargetExt = $TargetExt.ToLowerInvariant()
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($OutputPath)) | Out-Null

function Release-ComObject($Object) {
    if ($null -ne $Object) {
        try { [Runtime.InteropServices.Marshal]::FinalReleaseComObject($Object) | Out-Null } catch {}
    }
}

if ($Engine -eq 'word') {
    $app = $null; $doc = $null
    try {
        $app = New-Object -ComObject Word.Application
        $app.Visible = $false
        $app.DisplayAlerts = 0
        $doc = $app.Documents.Open($InputPath, $false, $true)
        $formats = @{ '.pdf'=17; '.docx'=16; '.doc'=0; '.rtf'=6; '.txt'=2; '.html'=10; '.odt'=23 }
        if (-not $formats.ContainsKey($TargetExt)) { throw "Word 대상 형식을 지원하지 않습니다: $TargetExt" }
        $doc.SaveAs2($OutputPath, $formats[$TargetExt])
    } finally {
        if ($null -ne $doc) { try { $doc.Close(0) } catch {} }
        if ($null -ne $app) { try { $app.Quit() } catch {} }
        Release-ComObject $doc; Release-ComObject $app
    }
}
elseif ($Engine -eq 'excel') {
    $app = $null; $book = $null
    try {
        $app = New-Object -ComObject Excel.Application
        $app.Visible = $false
        $app.DisplayAlerts = $false
        $book = $app.Workbooks.Open($InputPath, 0, $true)
        if ($TargetExt -eq '.pdf') {
            $book.ExportAsFixedFormat(0, $OutputPath)
        } else {
            $formats = @{ '.xlsx'=51; '.xls'=56; '.csv'=6; '.ods'=60; '.txt'=20 }
            if (-not $formats.ContainsKey($TargetExt)) { throw "Excel 대상 형식을 지원하지 않습니다: $TargetExt" }
            $book.SaveAs($OutputPath, $formats[$TargetExt])
        }
    } finally {
        if ($null -ne $book) { try { $book.Close($false) } catch {} }
        if ($null -ne $app) { try { $app.Quit() } catch {} }
        Release-ComObject $book; Release-ComObject $app
    }
}
elseif ($Engine -eq 'powerpoint') {
    $app = $null; $deck = $null
    try {
        $app = New-Object -ComObject PowerPoint.Application
        $deck = $app.Presentations.Open($InputPath, $true, $false, $false)
        $formats = @{ '.pdf'=32; '.pptx'=24; '.ppt'=1; '.odp'=35 }
        if (-not $formats.ContainsKey($TargetExt)) { throw "PowerPoint 대상 형식을 지원하지 않습니다: $TargetExt" }
        $deck.SaveAs($OutputPath, $formats[$TargetExt])
    } finally {
        if ($null -ne $deck) { try { $deck.Close() } catch {} }
        if ($null -ne $app) { try { $app.Quit() } catch {} }
        Release-ComObject $deck; Release-ComObject $app
    }
}
elseif ($Engine -eq 'hwp') {
    $hwp = $null
    try {
        $hwp = New-Object -ComObject HWPFrame.HwpObject
        try { $hwp.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule') | Out-Null } catch {}
        try { $hwp.XHwpWindows.Item(0).Visible = $false } catch {}
        # HWP 2022 exposes only the three-argument COM overload in PowerShell.
        $opened = $hwp.Open($InputPath, '', 'lock:false;forceopen:true;versionwarning:false;')
        if (-not $opened) { throw "한컴오피스에서 파일을 열지 못했습니다." }
        # Automatically accept non-security format compatibility notices.
        # File access security prompts are intentionally not bypassed here.
        try { $hwp.SetMessageBoxMode(0x00000010) | Out-Null } catch {}
        $formats = @{ '.pdf'='PDF'; '.hwp'='HWP'; '.hwpx'='HWPX'; '.docx'='OOXML'; '.txt'='UNICODE'; '.html'='HTML' }
        if (-not $formats.ContainsKey($TargetExt)) { throw "한컴 대상 형식을 지원하지 않습니다: $TargetExt" }
        $saved = $hwp.SaveAs($OutputPath, $formats[$TargetExt], '')
        if (-not $saved) { throw "한컴오피스가 저장을 완료하지 못했습니다." }
    } finally {
        if ($null -ne $hwp) { try { $hwp.Clear(1) } catch {}; try { $hwp.Quit() } catch {} }
        Release-ComObject $hwp
    }
}

Write-Output "OK: $OutputPath"
