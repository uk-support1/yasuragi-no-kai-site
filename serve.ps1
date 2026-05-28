# Simple static file server for local preview
param([int]$Port = 8080)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Start()
Write-Host "Serving at http://localhost:$Port/ (root: $root)"
Write-Host "Press Ctrl+C to stop."

$mimeTypes = @{
    ".html" = "text/html; charset=utf-8"
    ".css"  = "text/css"
    ".js"   = "application/javascript"
    ".json" = "application/json"
    ".png"  = "image/png"
    ".jpg"  = "image/jpeg"
    ".jpeg" = "image/jpeg"
    ".gif"  = "image/gif"
    ".svg"  = "image/svg+xml"
    ".ico"  = "image/x-icon"
    ".woff" = "font/woff"
    ".woff2"= "font/woff2"
    ".ttf"  = "font/ttf"
    ".pdf"  = "application/pdf"
}

while ($listener.IsListening) {
    try {
        $ctx  = $listener.GetContext()
        $req  = $ctx.Request
        $resp = $ctx.Response

        $urlPath = $req.Url.LocalPath
        if ($urlPath -eq "/") { $urlPath = "/index.html" }

        # Strip query string from path (cache-busting params)
        $urlPath = $urlPath -replace '\?.*', ''

        $filePath = Join-Path $root $urlPath.TrimStart("/").Replace("/", [System.IO.Path]::DirectorySeparatorChar)

        try {
            if (Test-Path $filePath -PathType Leaf) {
                $ext   = [System.IO.Path]::GetExtension($filePath)
                $mime  = if ($mimeTypes.ContainsKey($ext)) { $mimeTypes[$ext] } else { "application/octet-stream" }
                $bytes = [System.IO.File]::ReadAllBytes($filePath)
                $resp.ContentType     = $mime
                $resp.ContentLength64 = $bytes.LongLength
                $resp.OutputStream.Write($bytes, 0, $bytes.Length)
            } else {
                $resp.StatusCode = 404
                $msg = [System.Text.Encoding]::UTF8.GetBytes("404 Not Found: $urlPath")
                $resp.ContentLength64 = $msg.LongLength
                $resp.OutputStream.Write($msg, 0, $msg.Length)
            }
        } catch {
            # Ignore write errors (client disconnected, etc.)
        } finally {
            try { $resp.OutputStream.Close() } catch {}
        }
    } catch {
        # Ignore listener errors and keep serving
    }
}
