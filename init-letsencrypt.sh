#!/usr/bin/env bash
# =============================================================================
# init-letsencrypt.sh — Первичное получение SSL-сертификата от Let's Encrypt
#
# Использование:
#   ./init-letsencrypt.sh
#   CERTBOT_STAGING=1 ./init-letsencrypt.sh   # тест без реального сертификата
# =============================================================================
set -euo pipefail

DOMAIN="jobsearch.infoteq.ru"
EMAIL="${CERTBOT_EMAIL:-}"          # задайте через переменную окружения или .env
STAGING="${CERTBOT_STAGING:-0}"    # 1 = тест-режим (сертификат не будет валидным)
DATA_PATH="./nginx/certbot"

# ─── Цвета ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()  { echo -e "${CYAN}[INFO]${RESET}  $*"; }
ok()    { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
die()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }

# ─── Проверки ─────────────────────────────────────────────────────────────────
[[ -f "docker-compose.yml" ]] || die "Запустите из корня проекта (где docker-compose.yml)"

if [[ -z "$EMAIL" ]]; then
  # Пробуем прочитать из .env
  if [[ -f .env ]]; then
    EMAIL=$(grep -oP '^CERTBOT_EMAIL=\K.*' .env 2>/dev/null || true)
  fi
fi
[[ -n "$EMAIL" ]] || die "Укажите email: CERTBOT_EMAIL=you@example.com ./init-letsencrypt.sh"

# ─── Определение docker compose ───────────────────────────────────────────────
if docker compose version &>/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
  COMPOSE="docker-compose"
else
  die "docker compose не найден"
fi

echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════${RESET}"
echo -e "${BOLD}${CYAN}  Let's Encrypt — получение SSL-сертификата${RESET}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════${RESET}"
echo ""
info "Домен:  $DOMAIN"
info "Email:  $EMAIL"
[[ "$STAGING" == "1" ]] && warn "Тест-режим: сертификат будет self-signed (не добавится в браузер)"

# ─── Проверка: сертификат уже существует? ─────────────────────────────────────
if [[ -d "$DATA_PATH/conf/live/$DOMAIN" ]]; then
  warn "Сертификат уже существует в $DATA_PATH/conf/live/$DOMAIN"
  warn "Для принудительного перевыпуска удалите эту директорию и запустите снова."
  exit 0
fi

# ─── Подготовка директорий ────────────────────────────────────────────────────
info "Создаю директории для certbot..."
mkdir -p "$DATA_PATH/conf" "$DATA_PATH/www"
ok "Директории готовы"

# ─── Временный self-signed сертификат (чтобы nginx мог стартовать) ────────────
info "Создаю временный self-signed сертификат для $DOMAIN..."
mkdir -p "$DATA_PATH/conf/live/$DOMAIN"
$COMPOSE run --rm --no-deps --entrypoint \
  "openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
    -out    /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
    -subj '/CN=localhost'" \
  certbot
ok "Временный сертификат создан"

# ─── Запуск nginx с временным сертификатом ────────────────────────────────────
info "Запускаю nginx..."
$COMPOSE up --force-recreate -d nginx
ok "nginx запущен"

# ─── Удаляем временный сертификат ─────────────────────────────────────────────
info "Удаляю временный сертификат..."
$COMPOSE run --rm --no-deps --entrypoint \
  "rm -rf /etc/letsencrypt/live/$DOMAIN \
          /etc/letsencrypt/archive/$DOMAIN \
          /etc/letsencrypt/renewal/$DOMAIN.conf" \
  certbot
ok "Временный сертификат удалён"

# ─── Получаем настоящий сертификат ────────────────────────────────────────────
STAGING_FLAG=""
[[ "$STAGING" == "1" ]] && STAGING_FLAG="--staging"

info "Запрашиваю сертификат Let's Encrypt..."
$COMPOSE run --rm --no-deps --entrypoint \
  "certbot certonly --webroot \
    -w /var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    $STAGING_FLAG \
    -d $DOMAIN" \
  certbot
ok "Сертификат получен!"

# ─── Перезагружаем nginx с реальным сертификатом ──────────────────────────────
info "Перезагружаю nginx..."
$COMPOSE exec nginx nginx -s reload
ok "nginx перезагружен"

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${GREEN}║  Готово! Сайт доступен по адресу:                   ║${RESET}"
echo -e "${BOLD}${GREEN}║  https://$DOMAIN                    ║${RESET}"
echo -e "${BOLD}${GREEN}╠══════════════════════════════════════════════════════╣${RESET}"
echo -e "${BOLD}${GREEN}║  Сертификат обновляется автоматически каждые 12 ч.  ║${RESET}"
echo -e "${BOLD}${GREEN}║  (certbot renew запускается в фоне через Docker)    ║${RESET}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════╝${RESET}"
echo ""
