---
name: host-runtime-verify
description: РњСѓР»СЊС‚РёСЃС‚РµРєРѕРІР°СЏ СЃР±РѕСЂРєР°, Р·Р°РїСѓСЃРє РЅР° С…РѕСЃС‚Рµ Windows, healthcheck Рё Р°РЅР°Р»РёР· Р»РѕРіРѕРІ.
---
1. РћРїСЂРµРґРµР»Рё СЃС‚РµРє Рё СЂР°Р±РѕС‡РёР№ РїРѕСЂС‚ (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 3000/8080).
2. Р—Р°РІРµСЂС€Рё Р·Р°РІРёСЃС€РёРµ РїСЂРѕС†РµСЃСЃС‹:
   Get-NetTCPConnection -LocalPort <PORT> -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
3. Р—Р°РїСѓСЃС‚Рё СЃРµСЂРІРёСЃ РІ С„РѕРЅРµ СЃ РїРµСЂРµРЅР°РїСЂР°РІР»РµРЅРёРµРј РІС‹РІРѕРґР° РІ runtime_test.log.
4. РџРѕРґРѕР¶РґРё 3вЂ“5 СЃРµРєСѓРЅРґ, РїСЂРѕРІРµСЂСЊ Р»РѕРі РЅР° РїР°РЅРёРєРё Рё РёСЃРєР»СЋС‡РµРЅРёСЏ:
   Select-String -Path "runtime_test.log" -Pattern "exception","panic","fatal","traceback" -SimpleMatch
5. РћРїСЂРѕСЃРё СЌРЅРґРїРѕРёРЅС‚: curl.exe -sf http://localhost:<PORT>/health
6. РћСЃС‚Р°РЅРѕРІРё С‚РµСЃС‚РѕРІС‹Р№ РїСЂРѕС†РµСЃСЃ Рё СѓРґР°Р»Рё РІСЂРµРјРµРЅРЅС‹Р№ Р»РѕРі.
