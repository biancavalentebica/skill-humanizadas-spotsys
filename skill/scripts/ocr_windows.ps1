# OCR nativo do Windows (sem instalar nada): devolve as linhas/palavras com caixa em JSON.
# Uso: powershell -File ocr_windows.ps1 <imagem.png> <saida.json> [escala]
param([string]$img, [string]$out, [double]$escala = 1.0)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, [Type]$t) { $task = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(-1) | Out-Null; $task.Result }
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync((Resolve-Path $img).Path)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$dec = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bmp = Await ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$eng = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$res = Await ($eng.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
$linhas = @()
foreach ($l in $res.Lines) {
  $ws = @(); foreach ($w in $l.Words) { $r = $w.BoundingRect; $ws += [pscustomobject]@{ t = $w.Text; x = $r.X / $escala; y = $r.Y / $escala; w = $r.Width / $escala; h = $r.Height / $escala } }
  $linhas += [pscustomobject]@{ texto = $l.Text; palavras = $ws }
}
$linhas | ConvertTo-Json -Depth 5 | Out-File -Encoding utf8 $out
