# Инструкция по развёртыванию на Ubuntu (виртуальная машина в облаке)

## Требования
- Ubuntu 22.04 LTS (или 20.04)
- Минимум 2 GB RAM
- 20 GB SSD

## 1. Подготовка сервера

### Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

### Установка Docker (ПРОСТОЙ СПОСОБ)
```bash
sudo apt update
sudo apt install -y docker.io docker-compose


```

### Установка Docker (альтернативный способ)
Если нужен более новый Docker, можно установить из официального репозитория:
```bash
# Установка зависимостей
sudo apt install -y ca-certificates curl gnupg lsb-release

# Добавить ключ
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Добавить репозиторий
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu jammy stable" | sudo tee /etc/apt/sources.list.d/docker.list

# Установить
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
```

### Проверка Docker
```bash
sudo docker --version
sudo docker compose version
```

## 2. Настройка файрвола (рекомендуется)
```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw allow 5000/tcp # Приложение
sudo ufw enable
sudo ufw status
```

## 3. Развёртывание приложения

### Клонирование проекта
```bash
cd /opt
sudo git clone https://your-repo-url.git events-app
cd events-app
```

### Настройка переменных окружения
```bash
cp env.example .env
nano .env
```

Заполните `.env`:
```
POSTGRES_DB=events_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=придумайте_сложный_пароль
DATABASE_URL=postgresql://postgres:ваш_пароль@db:5432/events_db
SECRET=придумайте_secret_key_минимум_32_символа
YANDEX_API=ваш_api_ключ_яндекс
KUDAGO_API=https://kudago.com/api/1.1
```

### Запуск
```bash
sudo docker compose up -d --build
```

### Проверка статуса
```bash
sudo docker compose ps
sudo docker compose logs -f web
```

## 4. Первый запуск

### Инициализация БД
```bash
# Подключаемся к контейнеру БД
sudo docker exec -it events-app-db-1 psql -U postgres -d events_db

# Выполняем SQL
\i sql.sql
# или
\i /docker-entrypoint-initdb.d/init.sql
```

### Создание админа
```bash
# Через веб-интерфейс: http://ваш_ip:5000/register
```

## 5. Обновление приложения
```bash
cd /opt/events-app
sudo git pull
sudo docker compose up -d --build
```

## 6. Мониторинг и логи

### Просмотр логов
```bash
# Все сервисы
sudo docker compose logs -f

# Только веб
sudo docker compose logs -f web

# Только БД
sudo docker compose logs -f db
```

### Мониторинг ресурсов
```bash
sudo docker stats
```

## 7. Настройка Nginx (рекомендуется для прода)

### Установка Nginx
```bash
sudo apt install -y nginx
```

### Конфиг Nginx
```bash
sudo nano /etc/nginx/sites-available/events-app
```

```nginx
server {
    listen 80;
    server_name ваш_домен_или_ip;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Активация
```bash
sudo ln -s /etc/nginx/sites-available/events-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 8. Автозагрузка при перезагрузке сервера

```bash
sudo docker compose up -d
```

Docker настроен на автоперезапуск благодаря `restart: unless-stopped`.

## Troubleshooting

### Не запускается контейнер
```bash
sudo docker compose logs web
```

### Проблемы с БД
```bash
sudo docker compose restart db
sudo docker exec -it events-app-db-1 psql -U postgres -d events_db -c "SELECT 1"
```

### Очистка и пересборка
```bash
sudo docker compose down
sudo docker compose up -d --build --no-cache
```

### Просмотр использованных портов
```bash
sudo netstat -tulpn | grep LISTEN
```

## Безопасность

1. **Не храните пароли в git** - используйте `.env` и добавьте его в `.gitignore`
2. **Регулярно обновляйте образы**:
   ```bash
   sudo docker compose pull
   sudo docker compose up -d
   ```
3. **Настройте бэкапы БД** (опционально):
   ```bash
   sudo docker exec events-app-db-1 pg_dump -U postgres events_db > backup_$(date +%Y%m%d).sql
   ```

---

Дата создания: 2025
Автор: Тарасова С.А.