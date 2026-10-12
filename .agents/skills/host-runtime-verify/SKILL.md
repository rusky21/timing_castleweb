---
name: host-runtime-verify
description: РЎРѕР±РёСЂР°РµС‚ РїСЂРѕРµРєС‚, Р·Р°РїСѓСЃРєР°РµС‚ РІ С„РѕРЅРµ, РѕРїСЂР°С€РёРІР°РµС‚ healthcheck Рё СЃРєР°РЅРёСЂСѓРµС‚ Р»РѕРіРё РЅР° Windows.
---
# РђР›Р“РћР РРўРњ РџР РћР’Р•Р РљР Р РђРќРўРђР™РњРђ (WINDOWS)
1. РћРїСЂРµРґРµР»Рё СЃС‚РµРє Рё СЂР°Р±РѕС‡РёР№ РїРѕСЂС‚ СЃРµСЂРІРёСЃР° (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 8080/3000/8000).
2. Р‘РµР·РѕРїР°СЃРЅРѕ Р·Р°РІРµСЂС€Рё Р·Р°РІРёСЃС€РёРµ РїСЂРѕС†РµСЃСЃС‹ РЅР° С†РµР»РµРІРѕРј РїРѕСЂС‚Сѓ:
   Get-NetTCPConnection -LocalPort <PORT> -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
3. РЎРѕР±РµСЂРё РїСЂРѕРµРєС‚ (`npm run build`, `go build`, `tsc`).
4. Р—Р°РїСѓСЃС‚Рё СЃРµСЂРІРёСЃ РІ С„РѕРЅРµ СЃ РІС‹РІРѕРґРѕРј РІ Р»РѕРі:
   $proc = Start-Process -FilePath "<EXECUTABLE>" -ArgumentList "<ARGS>" -RedirectStandardOutput "runtime_test.log" -RedirectStandardError "runtime_test.log" -PassThru
5. РџРѕРґРѕР¶РґРё 3вЂ“5 СЃРµРєСѓРЅРґ.
6. РџСЂРѕРІРµСЂСЊ Р»РѕРі РЅР° РєСЂРёС‚РёС‡РµСЃРєРёРµ РѕС€РёР±РєРё:
   Select-String -Path "runtime_test.log" -Pattern "exception","panic","fatal","traceback","unhandledRejection" -SimpleMatch
7. РћРїСЂРѕСЃРё СЌРЅРґРїРѕРёРЅС‚ РіРѕС‚РѕРІРЅРѕСЃС‚Рё:
   curl.exe -sf -o NUL -w "%{http_code}" http://localhost:<PORT>/health
8. Р—Р°РІРµСЂС€Рё РїСЂРѕС†РµСЃСЃ Рё СѓРґР°Р»Рё С‚РµСЃС‚РѕРІС‹Р№ Р»РѕРі:
   Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue; Remove-Item -Force "runtime_test.log" -ErrorAction SilentlyContinue
