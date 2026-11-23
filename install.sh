#!/usr/bin/env bash
# Установка и автозапуск бота на сервере Debian/Ubuntu.
# Запускать из папки с bot.py:  bash install.sh
set -e

if [ ! -f bot.py ]; then
  echo "Ошибка: запустите скрипт в папке, где лежит bot.py"
  exit 1
fi

echo "== Установка Python =="
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip

echo
echo "== Настройка бота =="
read -r -p "Токен бота (от @BotFather): " BOT_TOKEN < /dev/tty
read -r -p "Ваш Telegram ID: " ADMIN_ID < /dev/tty
read -r -p "Ссылка на канал с отзывами: " REVIEWS_URL < /dev/tty

cat > .env <<EOF
BOT_TOKEN=${BOT_TOKEN}
ADMIN_ID=${ADMIN_ID}
REVIEWS_URL=${REVIEWS_URL}
EOF
chmod 600 .env

echo "== Установка библиотек =="
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "== Автозапуск =="
DIR="$(pwd)"
USER_NAME="$(whoami)"
sudo tee /etc/systemd/system/vapebot.service > /dev/null <<EOF
[Unit]
Description=Telegram shop bot
After=network-online.target
Wants=network-online.target

[Service]
User=${USER_NAME}
WorkingDirectory=${DIR}
ExecStart=${DIR}/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now vapebot
sleep 3
sudo systemctl status vapebot --no-pager | head -n 12

echo
echo "Готово. Бот запущен и будет стартовать сам после перезагрузки."
echo "Логи: sudo journalctl -u vapebot -f"
