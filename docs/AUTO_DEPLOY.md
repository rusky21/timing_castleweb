# Автодеплой CASTLEWEB на VDS

Workflow `.github/workflows/ci-cd.yml` запускает CI для pull request и push, а после успешных проверок автоматически деплоит push в ветку `main`. Деплой также можно запустить вручную через **Actions → CASTLEWEB CI/CD → Run workflow**.

## 1. Однократная подготовка сервера

Сначала выполните обычный production-деплой, чтобы создать `.env`, SSL-сертификаты и Docker volumes:

```bash
git clone https://github.com/rusky21/timing_castleweb.git "$HOME/castleweb"
cd "$HOME/castleweb"
sudo ./scripts/deploy.sh --full
```

Пользователь, под которым GitHub Actions подключается к VDS, должен:

- иметь доступ по SSH-ключу;
- иметь права записи в каталог репозитория;
- запускать `docker` без интерактивного `sudo` (обычно членство в группе `docker`);
- иметь в checkout ветку `main` и remote `origin` с доступом на чтение репозитория.

Если первоначальный `deploy.sh` запускался через `sudo`, перед первым автодеплоем передайте checkout deploy-пользователю и добавьте его в Docker group (замените пользователя и путь на свои):

```bash
sudo chown -R deploy:deploy /home/deploy/castleweb
sudo usermod -aG docker deploy
```

После изменения групп нужно заново войти по SSH. Не делайте `.env` доступными другим пользователям: достаточно владельца с режимом `600`.

Проверьте это от имени deploy-пользователя:

```bash
cd "$HOME/castleweb"
git branch --show-current
git fetch origin main
docker compose version
docker ps
test -f apps/backend/.env
test -f apps/parser/.env
```

Ожидаемая ветка — `main`. Оба `.env` остаются только на сервере и не перезаписываются workflow.

## 2. SSH-ключ и fingerprint

Создайте отдельный ключ без интерактивного passphrase для CI и добавьте публичную часть в `~/.ssh/authorized_keys` deploy-пользователя. Приватную часть сохраните только в GitHub Secret `PROD_SSH_KEY`.

Fingerprint сервера лучше получить непосредственно на VDS:

```bash
sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256
```

Скопируйте значение вида `SHA256:...` в Secret `PROD_HOST_FINGERPRINT`. Проверка fingerprint защищает SSH-деплой от подключения к подменённому хосту.

## 3. GitHub Environment, Secrets и Variables

В репозитории откройте **Settings → Environments** и используйте environment `prod`, затем добавьте secrets:

| Secret | Значение |
|---|---|
| `PROD_HOST` | IP или hostname VDS |
| `PROD_USER` | SSH-пользователь для деплоя |
| `PROD_SSH_KEY` | Полный приватный SSH-ключ, включая строки BEGIN/END |
| `PROD_PORT` | SSH-порт; необязательно, по умолчанию `22` |

Добавьте environment variables:

| Variable | Значение |
|---|---|
| `PROD_PATH` | Абсолютный путь к checkout, например `/home/deploy/castleweb`; если пусто, используется `$HOME/castleweb` |
| `PROD_URL` | URL сайта для ссылки в GitHub Deployments, например `https://castleweb.ru` |
| `PROD_HEALTH_URL` | Публичная проверка после деплоя, например `https://castleweb.ru/api/v1/health` |

Проверенный SHA256 fingerprint текущего VDS закреплён прямо в workflow: это публичный идентификатор SSH host key, а не секрет. При замене сервера обновите значение `fingerprint` в `.github/workflows/ci-cd.yml`. Для `prod` при желании включите required reviewers. GitHub применит правила environment до выдачи job доступа к production secrets.

## 4. Что делает безопасный deploy-скрипт

`scripts/auto-deploy.sh`:

- использует lock-файл и не допускает два одновременных деплоя;
- принимает от GitHub полный commit SHA и проверяет, что он принадлежит `origin/main`;
- останавливается при неожиданных правках tracked-файлов на сервере;
- передаёт `apps/backend/.env` через `docker compose --env-file`, поэтому Compose не использует демонстрационные fallback-секреты;
- собирает frontend во временной директории и атомарно переключает игнорируемый runtime-каталог `.deploy/frontend`, не меняя tracked `apps/frontend/dist`;
- собирает backend и LeadHunter до переключения runtime;
- запускает миграции и health-check обоих приложений;
- при неуспешном health-check возвращает предыдущий frontend и предыдущие Docker images, затем завершает workflow с ошибкой.

Миграции базы данных автоматически не откатываются: новые миграции должны быть обратно совместимыми хотя бы с предыдущей версией приложения. В `docker-compose.prod.yml` уже работает отдельный контейнер резервного копирования PostgreSQL.

## 5. Первый запуск и диагностика

После добавления Secrets/Variables запустите workflow вручную или отправьте commit в `main`. Успех подтверждается зелёным job `Deploy production` и строкой `Deployment <sha> completed successfully`.

Если деплой завершился ошибкой, смотрите лог job в GitHub Actions. На сервере полезны команды:

```bash
cd "$HOME/castleweb"
docker compose --env-file apps/backend/.env -f docker-compose.prod.yml ps
docker compose --env-file apps/backend/.env -f docker-compose.prod.yml logs --tail=200 backend leadhunter nginx
```

Workflow намеренно падает, а не пропускает deploy, если обязательные production secrets не настроены.
