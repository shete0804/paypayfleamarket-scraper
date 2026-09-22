# Test PayPay Flea Market response
$keyword = "メガルカリオex MUR メガブレイブ"
$encoded = [System.Web.HttpUtility]::UrlEncode($keyword)
$url = "https://paypayfleamarket.yahoo.co.jp/search/$encoded"

Write-Host "Fetching: $url"

try {
    $response = Invoke-WebRequest -Uri $url -UserAgent "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" -TimeoutSec 10

    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Content length: $($response.Content.Length)"

    # Save HTML to file for inspection
    $response.Content | Out-File "paypayfleamarket_response.html" -Encoding UTF8
    Write-Host "Response saved to paypayfleamarket_response.html"

    # Search for JSON-LD
    $html = $response.Content
    if ($html -match '<script type="application/ld\+json">([^<]+)</script>') {
        Write-Host "JSON-LD schema found"
        $jsonStr = $matches[1]
        Write-Host "JSON-LD size: $($jsonStr.Length) bytes"
        $preview = $jsonStr.Substring(0, [Math]::Min(200, $jsonStr.Length))
        Write-Host "First 200 chars: $preview"
    } else {
        Write-Host "JSON-LD schema NOT found"
    }

    # Count <a href="/item/"> tags
    $itemLinks = [regex]::Matches($html, '<a[^>]*href="/item/[^"]*"')
    Write-Host "Found $($itemLinks.Count) item links"

} catch {
    Write-Host "Error: $_"
}
