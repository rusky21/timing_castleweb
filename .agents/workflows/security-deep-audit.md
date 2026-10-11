---
description: Проверяет diff на уязвимости (BOLA/IDOR, SQLi, утечки данных, SSRF).
---
1. Вызови git diff HEAD~1.
2. Проверь BOLA/IDOR, инъекции, открытые токены и SSRF.
3. Верни вердикт VERIFICATION_PASSED или VERIFICATION_FAILED с эксплойтом и фиксом.
