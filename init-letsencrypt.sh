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
[[ "$STAGING" == "1" ]] && warn "Тест-режим: сертификат не будет валидным в браузере"

# ─── Проверка: сертификат уже существует? ─────────────────────────────────────
if [[ -d "$DATA_PATH/conf/live/$DOMAIN" ]]; then
  warn "Сертификат уже существует в $DATA_PATH/conf/live/$DOMAIN"
  warn "Для принудительного перевыпуска удалите эту директорию и запустите снова."
  exit 0
fi

# ─── Preflight: доступность порта 80 снаружи ──────────────────────────────────
check_port_80() {
  info "Проверяю доступность порта 80 снаружи..."
  # Пробуем достучаться до ACME-challenge пути с самого сервера через публичный IP
  local http_code
  http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
    "http://${DOMAIN}/.well-known/acme-challenge/preflight-test" 2>/dev/null || echo "000")

  if [[ "$http_code" == "000" ]]; then
    echo ""
    echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${RED}║  ОШИБКА: Порт 80 недоступен снаружи                         ║${RESET}"
    echo -e "${RED}╠══════════════════════════════════════════════════════════════╣${RESET}"
    echo -e "${RED}║  Let's Encrypt не сможет пройти HTTP-01 challenge            ║${RESET}"
    echo -e "${RED}║                                                              ║${RESET}"
    echo -e "${RED}║  Проверьте и исправьте:                                      ║${RESET}"
    echo -e "${RED}║  1. Firewall на сервере:                                     ║${RESET}"
    echo -e "${RED}║     sudo ufw allow 80/tcp && sudo ufw allow 443/tcp          ║${RESET}"
    echo -e "${RED}║     sudo ufw reload                                          ║${RESET}"
    echo -e "${RED}║  2. Security Group / Network ACL облачного провайдера:       ║${RESET}"
    echo -e "${RED}║     Разрешите inbound TCP 80 и 443 из 0.0.0.0/0             ║${RESET}"
    echo -e "${RED}║  3. Убедитесь, что DNS $DOMAIN → IP этого сервера  ║${RESET}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${RESET}"
    echo ""
    die "Устраните блокировку порта 80 и запустите скрипт снова."
  fi

  # 404 = nginx работает, путь просто не существует — это нормально
  ok "Порт 80 доступен (HTTP $http_code)"
}

# ─── Ожидание готовности nginx ────────────────────────────────────────────────
wait_for_nginx() {
  info "Жду готовности nginx на порту 80..."
  local retries=30
  while [[ $retries -gt 0 ]]; do
    if curl -sf --max-time 2 "http://127.0.0.1/" &>/dev/null || \
       curl -s  --max-time 2 "http://127.0.0.1/" -o /dev/null -w "%{http_code}" 2>/dev/null | grep -q '^[0-9]'; then
      ok "nginx отвечает"
      return 0
    fi
    retries=$((retries - 1))
    echo -n "."
    sleep 2
  done
  echo ""
  warn "nginx не отвечает за 60 секунд. Проверьте логи: $COMPOSE logs nginx"
  $COMPOSE ps
  die "nginx не поднялся"
}

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

# ─── Запускаем все сервисы ────────────────────────────────────────────────────
info "Запускаю все сервисы (включая nginx)..."
$COMPOSE up -d
ok "Сервисы запущены"

# ─── Ждём, пока nginx реально готов ──────────────────────────────────────────
wait_for_nginx

# ─── Проверяем, что порт 80 доступен снаружи ─────────────────────────────────
check_port_80

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
