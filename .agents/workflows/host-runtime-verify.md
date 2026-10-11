---
description: Мультистековая сборка, запуск на хосте Windows, healthcheck и анализ логов.
---
1. Определи стек и порт (3000/8000/8080).
2. Заверши зависшие процессы: Get-NetTCPConnection -LocalPort <PORT> -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
3. Запусти сервис в фоне, перенаправив вывод в runtime_test.log.
4. Подожди 3-5 секунд, проверь логи на exception/panic/fatal.
5. Опроси эндпоинт: curl.exe -sf http://localhost:<PORT>/health
6. Заверши тестовый процесс и удали временный лог.
