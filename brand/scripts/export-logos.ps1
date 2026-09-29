# Renders the logo SVGs and lockups to PNG with headless Edge (transparent background).
# Run from the repo root: powershell -File brand/scripts/export-logos.ps1
$root = (Resolve-Path "brand/assets/logo").Path
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$prof = Join-Path $env:TEMP "urbora-edge"
function Shot($url, $png, $w, $h) {
  Start-Process -FilePath $edge -Wait -ArgumentList "--headless=new","--disable-gpu","--hide-scrollbars","--user-data-dir=$prof","--default-background-color=00000000","--virtual-time-budget=8000","--screenshot=$png","--window-size=$w,$h",$url
}
$u = "file:///" + $root.Replace([char]92, [char]47)
foreach ($s in 512, 192, 64) {
  Set-Content -Encoding utf8 "$root\_tmp.html" "<body style='margin:0'><img src='mark.svg' width=$s height=$s>"
  Shot "$u/_tmp.html" "$root\png\mark-$s.png" $s $s
}
Set-Content -Encoding utf8 "$root\_tmp.html" "<body style='margin:0;background:#0D3B2E'><div style='width:512px;height:512px;display:grid;place-items:center'><img src='mark.svg' width=360 height=360></div>"
Shot "$u/_tmp.html" "$root\png\app-icon-maskable-512.png" 512 512
Shot "$u/lockups.html" "$root\png\_sheet.png" 1100 1060
Remove-Item "$root\_tmp.html"
# Cut the sheet into one PNG per lockup (bands: horizontal, horizontal on dark, stacked).
python -c "from PIL import Image;im=Image.open('brand/assets/logo/png/_sheet.png').convert('RGBA');[im.crop((0,a,1100,b)).crop(im.crop((0,a,1100,b)).getbbox()).save('brand/assets/logo/png/'+n+'.png') for n,a,b in (('lockup-horizontal',0,262),('lockup-horizontal-on-dark',262,530),('lockup-stacked',530,1040))]"
Remove-Item "brand/assets/logo/png/_sheet.png"
