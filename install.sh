#!/usr/bin/env bash
# =============================================================================
# JobAutoApply — автоматическая установка и запуск
# =============================================================================
set -euo pipefail

# ─── Цвета ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
die()     { error "$*"; exit 1; }
header()  { echo -e "\n${BOLD}${CYAN}══════════════════════════════════════${RESET}"; \
            echo -e "${BOLD}${CYAN}  $*${RESET}"; \
            echo -e "${BOLD}${CYAN}══════════════════════════════════════${RESET}\n"; }

# ─── Проверка ОС ──────────────────────────────────────────────────────────────
detect_os() {
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v apt-get &>/dev/null; then
      OS="debian"
    elif command -v dnf &>/dev/null; then
      OS="fedora"
    elif command -v pacman &>/dev/null; then
      OS="arch"
    else
      OS="linux"
    fi
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
  else
    die "Неподдерживаемая ОС: $OSTYPE"
  fi
  info "ОС: $OS"
}

# ─── Зависимости ─────────────────────────────────────────────────────────────
check_deps() {
  header "Проверка зависимостей"
  local missing=()

  for cmd in docker git curl; do
    if command -v "$cmd" &>/dev/null; then
      success "$cmd найден"
    else
      missing+=("$cmd")
      error "$cmd не найден"
    fi
  done

  # Docker Compose (v2 plugin или standalone)
  if docker compose version &>/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
    success "docker compose (v2) найден"
  elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
    success "docker-compose (v1) найден"
  else
    missing+=("docker-compose")
    error "docker compose не найден"
  fi

  if [[ ${#missing[@]} -gt 0 ]]; then
    warn "Отсутствующие зависимости: ${missing[*]}"
    install_deps "${missing[@]}"
  fi
}

install_deps() {
  local deps=("$@")
  info "Установка: ${deps[*]}"

  case "$OS" in
    debian)
      sudo apt-get update -qq
      for dep in "${deps[@]}"; do
        case "$dep" in
          docker)
            install_docker_debian ;;
          git)
            sudo apt-get install -y git ;;
          curl)
            sudo apt-get install -y curl ;;
        esac
      done ;;
    fedora)
      for dep in "${deps[@]}"; do
        case "$dep" in
          docker)
            sudo dnf -y install docker docker-compose-plugin
            sudo systemctl enable --now docker ;;
          git)
            sudo dnf -y install git ;;
          curl)
            sudo dnf -y install curl ;;
        esac
      done ;;
    macos)
      if ! command -v brew &>/dev/null; then
        info "Устанавливаю Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      fi
      for dep in "${deps[@]}"; do
        case "$dep" in
          docker)
            warn "Установите Docker Desktop вручную: https://www.docker.com/products/docker-desktop/"
            die "Docker Desktop требует ручной установки на macOS" ;;
          git|curl)
            brew install "$dep" ;;
        esac
      done ;;
    *)
      die "Установите вручную: ${deps[*]}" ;;
  esac
}

install_docker_debian() {
  info "Устанавливаю Docker (официальный способ)..."
  sudo apt-get install -y ca-certificates curl gnupg lsb-release

  sudo mkdir -p /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo apt-get update -qq
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER"
  warn "Добавлен в группу docker. Перезайдите в систему для применения."
  COMPOSE_CMD="docker compose"
}

# ─── Настройка .env ───────────────────────────────────────────────────────────
setup_env() {
  header "Настройка переменных окружения"

  if [[ -f .env ]]; then
    warn ".env уже существует"
    read -rp "Перезаписать? [y/N] " ans
    [[ "$ans" =~ ^[Yy]$ ]] || { info "Используем существующий .env"; return; }
  fi

  cp .env.example .env
  success ".env создан из .env.example"

  # Генерируем SECRET_KEY
  if command -v openssl &>/dev/null; then
    SECRET_KEY=$(openssl rand -hex 32)
  else
    SECRET_KEY=$(tr -dc 'a-f0-9' < /dev/urandom | head -c 64 2>/dev/null || echo "change-me-$(date +%s)")
  fi

  sed_inplace "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|" .env
  success "SECRET_KEY сгенерирован"

  # Определяем IP и прописываем ALLOWED_ORIGINS в JSON-формате (требует pydantic-settings)
  MACHINE_IP=$(detect_ip)
  ALLOWED_ORIGINS='["https://jobsearch.infoteq.ru"]'
  sed_inplace "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=${ALLOWED_ORIGINS}|" .env
  success "ALLOWED_ORIGINS установлен: ${ALLOWED_ORIGINS}"

  # Запрашиваем email для certbot (Let's Encrypt)
  read -rp "Введите email для Let's Encrypt (SSL-уведомления): " certbot_email
  if [[ -n "$certbot_email" ]]; then
    sed_inplace "s|^CERTBOT_EMAIL=.*|CERTBOT_EMAIL=${certbot_email}|" .env
    success "CERTBOT_EMAIL сохранён"
  else
    warn "CERTBOT_EMAIL не задан — заполните его в .env перед запуском init-letsencrypt.sh"
  fi

  echo ""
  echo -e "${YELLOW}┌─────────────────────────────────────────────┐${RESET}"
  echo -e "${YELLOW}│  Для работы с hh.ru API нужны OAuth-ключи  │${RESET}"
  echo -e "${YELLOW}│  Получите их на: https://dev.hh.ru/admin    │${RESET}"
  echo -e "${YELLOW}└─────────────────────────────────────────────┘${RESET}"
  echo ""

  read -rp "Ввести HH_CLIENT_ID прямо сейчас? [y/N] " ans
  if [[ "$ans" =~ ^[Yy]$ ]]; then
    read -rp "  HH_CLIENT_ID:     " hh_id
    read -rp "  HH_CLIENT_SECRET: " hh_secret
    [[ -n "$hh_id" ]]     && sed_inplace "s|^HH_CLIENT_ID=.*|HH_CLIENT_ID=${hh_id}|" .env
    [[ -n "$hh_secret" ]] && sed_inplace "s|^HH_CLIENT_SECRET=.*|HH_CLIENT_SECRET=${hh_secret}|" .env
    success "hh.ru ключи сохранены"
  else
    warn "Не забудьте заполнить HH_CLIENT_ID и HH_CLIENT_SECRET в файле .env"
  fi

  read -rp "Ввести OPENAI_API_KEY для AI-писем? [y/N] " ans
  if [[ "$ans" =~ ^[Yy]$ ]]; then
    read -rp "  OPENAI_API_KEY: " oai_key
    [[ -n "$oai_key" ]] && sed_inplace "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${oai_key}|" .env
    success "OpenAI ключ сохранён"
  fi
}

# sed -i работает по-разному на Linux и macOS
sed_inplace() {
  if [[ "$OS" == "macos" ]]; then
    sed -i '' "$1" "$2"
  else
    sed -i "$1" "$2"
  fi
}

# ─── Определение IP-адреса машины ─────────────────────────────────────────────
detect_ip() {
  local ip=""

  # Метод 1: через маршрут до внешнего адреса (Linux, самый надёжный)
  if command -v ip &>/dev/null; then
    ip=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+' | head -1)
  fi

  # Метод 2: hostname -I (Linux)
  if [[ -z "$ip" ]] && command -v hostname &>/dev/null; then
    ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  fi

  # Метод 3: ipconfig getifaddr (macOS, en0 — Wi-Fi, en1 — Ethernet)
  if [[ -z "$ip" ]] && command -v ipconfig &>/dev/null; then
    ip=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)
  fi

  # Метод 4: ifconfig (универсальный fallback)
  if [[ -z "$ip" ]] && command -v ifconfig &>/dev/null; then
    ip=$(ifconfig 2>/dev/null \
      | grep 'inet ' \
      | grep -v '127\.0\.0\.1' \
      | awk '{print $2}' \
      | head -1)
  fi

  # Убираем prefixlen если ifconfig вернул addr/prefix
  ip="${ip%%/*}"

  echo "$ip"
}

# ─── Docker ──────────────────────────────────────────────────────────────────
check_docker_running() {
  if ! docker info &>/dev/null 2>&1; then
    if [[ "$OS" == "macos" ]]; then
      info "Запускаю Docker Desktop..."
      open -a Docker
      info "Жду запуска Docker"
      local retries=30
      while ! docker info &>/dev/null 2>&1; do
        sleep 2
        retries=$((retries - 1))
        [[ $retries -eq 0 ]] && die "Docker не запустился. Запустите Docker Desktop вручную."
        echo -n "."
      done
      echo ""
    else
      sudo systemctl start docker || die "Не удалось запустить Docker"
    fi
  fi
  success "Docker запущен"
}

# ─── Сборка и запуск ──────────────────────────────────────────────────────────
build_and_run() {
  header "Сборка и запуск контейнеров"

  info "Собираю образы (это может занять несколько минут)..."
  $COMPOSE_CMD build --parallel

  info "Запускаю сервисы..."
  $COMPOSE_CMD up -d

  success "Контейнеры запущены"
}

# ─── Ожидание готовности ──────────────────────────────────────────────────────
wait_for_backend() {
  header "Ожидание готовности бэкенда"
  local url="http://127.0.0.1:8000/health"
  local retries=40
  local wait=3

  info "Проверяю $url ..."
  while [[ $retries -gt 0 ]]; do
    if curl -sf "$url" &>/dev/null; then
      success "Бэкенд готов!"
      return 0
    fi
    retries=$((retries - 1))
    echo -n "."
    sleep "$wait"
  done
  echo ""
  warn "Бэкенд не ответил вовремя. Проверьте логи: $COMPOSE_CMD logs backend"
}

# ─── Статус ──────────────────────────────────────────────────────────────────
show_status() {
  header "Статус сервисов"
  $COMPOSE_CMD ps

  local ip
  ip=$(detect_ip)

  echo ""
  echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}${GREEN}║             JobAutoApply запущен!                    ║${RESET}"
  echo -e "${BOLD}${GREEN}╠══════════════════════════════════════════════════════╣${RESET}"
  echo -e "${BOLD}${GREEN}║  Сайт (HTTPS):  https://jobsearch.infoteq.ru        ║${RESET}"
  echo -e "${BOLD}${GREEN}║  API Docs:      https://jobsearch.infoteq.ru/api/docs║${RESET}"
  echo -e "${BOLD}${GREEN}╠══════════════════════════════════════════════════════╣${RESET}"
  echo -e "${BOLD}${GREEN}║  Следующий шаг: выпустить SSL-сертификат             ║${RESET}"
  echo -e "${BOLD}${GREEN}║  → ./init-letsencrypt.sh                             ║${RESET}"
  echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════╝${RESET}"
  echo ""
  echo -e "Полезные команды:"
  echo -e "  ${CYAN}$COMPOSE_CMD logs -f${RESET}          — логи всех сервисов"
  echo -e "  ${CYAN}$COMPOSE_CMD logs -f backend${RESET}  — логи только бэкенда"
  echo -e "  ${CYAN}$COMPOSE_CMD logs -f nginx${RESET}    — логи nginx"
  echo -e "  ${CYAN}$COMPOSE_CMD down${RESET}             — остановить"
  echo -e "  ${CYAN}$COMPOSE_CMD down -v${RESET}          — остановить и удалить данные"
  echo ""
}

# ─── Обновление (опционально) ─────────────────────────────────────────────────
update_mode() {
  header "Обновление JobAutoApply"
  info "Получаю последние изменения..."
  git pull origin "$(git branch --show-current)"
  info "Пересобираю образы..."
  $COMPOSE_CMD build --parallel
  info "Перезапускаю сервисы..."
  $COMPOSE_CMD up -d
  success "Обновление завершено"
}

# ─── Деинсталляция ────────────────────────────────────────────────────────────
uninstall_mode() {
  header "Удаление JobAutoApply"
  warn "Будут удалены контейнеры и тома (включая данные БД)!"
  read -rp "Вы уверены? [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || { info "Отменено"; return; }
  $COMPOSE_CMD down -v --remove-orphans
  success "Сервисы остановлены и данные удалены"
}

# ─── Справка ─────────────────────────────────────────────────────────────────
usage() {
  echo ""
  echo -e "${BOLD}Использование:${RESET} $0 [команда]"
  echo ""
  echo "Команды:"
  echo "  (без аргументов)   Полная установка и запуск"
  echo "  update             Обновить и перезапустить"
  echo "  uninstall          Остановить и удалить данные"
  echo "  status             Показать статус сервисов"
  echo "  logs               Показать логи"
  echo "  help               Справка"
  echo ""
}

# ─── Точка входа ─────────────────────────────────────────────────────────────
main() {
  echo ""
  echo -e "${BOLD}${RED}  ╔══════════════════════════════════╗${RESET}"
  echo -e "${BOLD}${RED}  ║      JobAutoApply Installer      ║${RESET}"
  echo -e "${BOLD}${RED}  ║   Автоматический отклик hh.ru    ║${RESET}"
  echo -e "${BOLD}${RED}  ╚══════════════════════════════════╝${RESET}"
  echo ""

  # Должны находиться в корне проекта
  [[ -f "docker-compose.yml" ]] || die "Запустите скрипт из корня проекта (там, где docker-compose.yml)"

  COMPOSE_CMD="docker compose"  # default, may be overridden in check_deps
  detect_os

  local cmd="${1:-install}"

  case "$cmd" in
    install|"")
      check_deps
      check_docker_running
      setup_env
      build_and_run
      wait_for_backend
      show_status ;;
    update)
      check_deps
      check_docker_running
      update_mode
      wait_for_backend
      show_status ;;
    uninstall)
      check_deps
      uninstall_mode ;;
    status)
      check_deps
      $COMPOSE_CMD ps ;;
    logs)
      check_deps
      $COMPOSE_CMD logs -f ;;
    help|--help|-h)
      usage ;;
    *)
      error "Неизвестная команда: $cmd"
      usage
      exit 1 ;;
  esac
}

main "$@"
