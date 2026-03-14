# Документация ansible-outline-deploy

## Содержание

1. [Требования](#требования)
2. [Установка](#установка)
3. [Настройка inventory](#настройка-inventory)
4. [Команды](#команды)
5. [Как работает management_url](#как-работает-management_url)
6. [Кастомный модуль outline_server](#кастомный-модуль-outline_server)
7. [Утилита get_outline_str](#утилита-get_outline_str)
8. [Идемпотентность](#идемпотентность)
9. [Безопасность](#безопасность)
10. [Устранение проблем](#устранение-проблем)

---

## Требования

**Control node** (машина, с которой запускается Ansible):
- Python 3.12+
- Linux или macOS (Windows — только через WSL)
- Сетевой доступ к серверам по SSH
- Сетевой доступ к Management API серверов (порт Outline)

**Managed nodes** (серверы, куда раскатывается Outline):
- Ubuntu 22.04 или 24.04
- Доступ в интернет (для скачивания Docker и образов Outline)
- SSH-доступ с control node

> **Windows пользователям:** Ansible не поддерживает Windows как control node.
> Установи [WSL](https://learn.microsoft.com/ru-ru/windows/wsl/install), открой
> терминал Ubuntu и работай оттуда. Путь к SSH-ключу будет вида
> `/mnt/c/Users/<user>/.ssh/id_rsa`.

---

## Установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/zeph1rr/ansible-outline-deploy.git
cd ansible-outline-deploy
```

### 2. Создать виртуальное окружение и установить зависимости

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Создать inventory

```bash
cp inventory/hosts.yml.example inventory/hosts.yml
```

Отредактируй `inventory/hosts.yml` — добавь свои серверы.

### 4. Проверить подключение

```bash
ansible vpn_servers -i inventory/hosts.yml -m ping
```

Ожидаемый ответ для каждого хоста:
```
my-server | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

---

## Настройка inventory

Все настройки хранятся в одном файле `inventory/hosts.yml`.
Используй `inventory/hosts.yml.example` как шаблон.

### Структура файла

```yaml
all:
  children:
    vpn_servers:
      vars:
        # SSH — применяется ко всем хостам группы
        ansible_user: root
        ansible_ssh_private_key_file: ~/.ssh/id_rsa
        ansible_python_interpreter: /usr/bin/python3

        # Outline — значения по умолчанию для всей группы
        outline_server_name: "Outline VPN"
        outline_metrics_enabled: false
        outline_default_port: ~          # ~ = не менять
        outline_default_limit_bytes: ~   # ~ = не менять; 0 = удалить лимит
        outline_hostname: ~              # ~ = использовать IP сервера

      hosts:
        my-server-1:
          ansible_host: 1.2.3.4
          outline_server_name: "EU Node 1"

        my-server-2:
          ansible_host: 5.6.7.8
          outline_server_name: "EU Node 2"
          outline_default_limit_bytes: 53687091200   # 50 GB
```

### Справочник SSH-переменных

| Переменная | Описание | Пример |
|---|---|---|
| `ansible_host` | IP или DNS-имя сервера | `1.2.3.4` |
| `ansible_user` | SSH-пользователь | `root` |
| `ansible_port` | SSH-порт | `2222` (по умолчанию `22`) |
| `ansible_ssh_private_key_file` | Путь к приватному SSH-ключу | `~/.ssh/id_rsa` |
| `ansible_ssh_pass` | SSH-пароль (альтернатива ключу) | `s3cr3t` |
| `ansible_python_interpreter` | Путь к Python на сервере | `/usr/bin/python3` |

### Справочник Outline-переменных

| Переменная | Описание | По умолчанию |
|---|---|---|
| `outline_server_name` | Отображаемое имя сервера | `"Outline VPN"` |
| `outline_hostname` | Hostname в ссылках доступа (`ss://`) | `~` — IP сервера |
| `outline_default_port` | Порт для новых ключей доступа | `~` — не менять |
| `outline_default_limit_bytes` | Лимит трафика в байтах; `0` = снять лимит | `~` — не менять |
| `outline_metrics_enabled` | Анонимная статистика для Jigsaw | `false` |
| `outline_management_url` | URL Management API (заполняется автоматически) | `~` |

### Приоритет переменных

Переменные на уровне хоста имеют приоритет над `vars` группы.
Это позволяет задавать общие настройки в `vars` и переопределять их для конкретных серверов.

### Примеры конфигураций хостов

**Минимальный** — только IP, всё из `vars`:
```yaml
my-server:
  ansible_host: 1.2.3.4
  outline_server_name: "EU Node"
```

**SSH по паролю с нестандартным портом:**
```yaml
my-server:
  ansible_host: 5.6.7.8
  ansible_port: 2222
  ansible_user: ubuntu
  ansible_ssh_pass: "s3cr3t"
  outline_server_name: "EU Node"
```

**С кастомным hostname и лимитом трафика:**
```yaml
my-server:
  ansible_host: 9.10.11.12
  outline_server_name: "EU Node"
  outline_hostname: "vpn.mycompany.com"
  outline_default_port: 8388
  outline_default_limit_bytes: 53687091200   # 50 GB
  outline_metrics_enabled: true
```

**Outline уже установлен** — management_url задан вручную:
```yaml
my-server:
  ansible_host: 11.22.33.44
  outline_management_url: "https://11.22.33.44:12345/AbCdEfGhIj"
  outline_server_name: "EU Node"
```

---

## Команды

### Полный деплой

Установка Docker + Outline + конфигурация:

```bash
ansible-playbook -i inventory/hosts.yml playbook.yml
```

### Только конфигурация

Outline уже установлен, нужно только изменить настройки.
Измени нужные переменные в `hosts.yml` и запусти:

```bash
ansible-playbook -i inventory/hosts.yml playbook.yml --skip-tags install
```

### Один хост

```bash
ansible-playbook -i inventory/hosts.yml playbook.yml --limit my-server
```

### Dry-run

Посмотреть что изменится без реального применения:

```bash
ansible-playbook -i inventory/hosts.yml playbook.yml --check --diff
```

### Деинсталляция

> ⚠️ Деструктивная операция. Все данные Outline (ключи, настройки) будут удалены безвозвратно.

```bash
# Все серверы
ansible-playbook -i inventory/hosts.yml uninstall.yml

# Один хост
ansible-playbook -i inventory/hosts.yml uninstall.yml --limit my-server

# Dry-run
ansible-playbook -i inventory/hosts.yml uninstall.yml --check
```

Деинсталляция выполняет:
1. Запрашивает подтверждение (Enter для продолжения, Ctrl+C для отмены)
2. Останавливает и удаляет Docker-контейнеры `shadowbox` и `watchtower`
3. Удаляет Docker-образы Outline
4. Удаляет директорию `/opt/outline` и утилиту `get_outline_str`
5. Удаляет `inventory/facts/<hostname>.yml` на control node

После деинсталляции хост остаётся в `inventory/hosts.yml` — можно сразу переразвернуть Outline командой `ansible-playbook playbook.yml --limit my-server`.

---

## Как работает management_url

Outline генерирует уникальный Management API URL при установке и записывает его в `/opt/outline/access.txt` на сервере.

```
Первый запуск playbook:
  1. SSH → устанавливает Docker и Outline
  2. Читает /opt/outline/access.txt с сервера
  3. Заменяет внешний IP на ansible_host в URL
  4. Обновляет access.txt на сервере
  5. Сохраняет URL в inventory/facts/<hostname>.yml на control node

Последующие запуски:
  1. pre_tasks загружает inventory/facts/<hostname>.yml
  2. management_url уже известен
  3. --skip-tags install применяет только конфигурацию через API
```

Файлы `inventory/facts/` содержат токен доступа к Management API.
Они исключены из git через `.gitignore`.

Если репозиторий **приватный** — можно закоммитить факты или зашифровать их:
```bash
ansible-vault encrypt inventory/facts/my-server.yml
# при запуске добавляй флаг:
ansible-playbook playbook.yml --ask-vault-pass
```

---

## Кастомный модуль outline_server

Файл: `roles/outline/library/outline_server.py`

Модуль использует [outline-vpn-api-client](https://github.com/Zeph1rr/outline-vpn-api-client)
для настройки сервера через Management API.

### Параметры

| Параметр | Тип | Описание |
|---|---|---|
| `management_url` | str | Management API URL (обязательный) |
| `server_name` | str | Новое имя сервера |
| `hostname` | str | Hostname для ссылок доступа |
| `default_port` | int | Порт для новых ключей |
| `default_limit_bytes` | int | Лимит трафика в байтах; `0` = снять |
| `metrics_enabled` | bool | Включить анонимную статистику |

### Возвращаемые значения

| Поле | Описание |
|---|---|
| `changed` | `true` если хотя бы одна настройка была изменена |
| `server_id` | Уникальный ID сервера |
| `server_name` | Имя сервера после изменений |
| `changes` | Список применённых изменений |

### Поведение

- **Идемпотентен**: сравнивает текущее состояние с желаемым, вызывает API только при расхождении
- **Поддерживает `--check`**: в режиме dry-run сообщает что изменилось бы, не применяя изменений
- **Запускается на control node** (`delegate_to: localhost`) — SSH до серверов нужен только для установки

---

## Утилита get_outline_str

После деплоя на каждом сервере доступна команда `get_outline_str`.

```bash
root@my-server:~# get_outline_str
{"apiUrl":"https://1.2.3.4:12345/AbCdEfGhIj","certSha256":"B818...661E3"}
```

Выводит `management_url` и `certSha256` — всё необходимое для подключения Outline Manager.

Файл скрипта: `roles/outline/files/get_outline_str.sh`
Устанавливается в: `/usr/local/bin/get_outline_str`

---

## Идемпотентность

Повторный запуск playbook безопасен — Ansible проверяет текущее состояние перед каждым действием.

| Ситуация | Поведение |
|---|---|
| Docker уже установлен | Шаги установки Docker пропускаются (`changed=false`) |
| Outline уже установлен | `install_server.sh` не запускается повторно (проверяется наличие `/opt/outline/access.txt`) |
| Настройки сервера совпадают с inventory | Модуль возвращает `changed=false`, API не вызывается |
| `outline_default_limit_bytes: 0` | Лимит **удаляется** с сервера |
| Параметр равен `~` (null) | Текущее значение на сервере **не трогается** |

---

## Безопасность

### Что не коммитить в публичный репозиторий

Файл `.gitignore` уже исключает:
- `inventory/hosts.yml` — содержит IP-адреса, имена пользователей, пароли
- `inventory/facts/` — содержит Management API URL с токеном доступа

### SSH-ключи

Используй SSH-ключи вместо паролей везде где возможно:
```bash
ssh-keygen -t ed25519 -C "ansible-outline"
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@your-server
```

Затем в `hosts.yml`:
```yaml
ansible_ssh_private_key_file: ~/.ssh/id_ed25519
```

### ansible-vault

Для хранения паролей и токенов в зашифрованном виде:
```bash
# Зашифровать файл с фактами
ansible-vault encrypt inventory/facts/my-server.yml

# Зашифровать отдельную переменную в hosts.yml
ansible-vault encrypt_string 's3cr3t' --name 'ansible_ssh_pass'

# Запуск с расшифровкой
ansible-playbook playbook.yml --ask-vault-pass
# или через файл с паролем
ansible-playbook playbook.yml --vault-password-file ~/.vault_pass
```

---

## Устранение проблем

### `ansible.cfg` игнорируется (world-writable directory)

```
[WARNING]: Ansible is being run in a world writable directory, ignoring it as an ansible.cfg source.
```

Директория имеет слишком широкие права. Исправить:
```bash
chmod 755 /path/to/ansible-outline-deploy
```

### `[WinError 1] Неверная функция`

Ansible не работает на Windows напрямую. Установи WSL:
```powershell
wsl --install
```
Затем работай из терминала Ubuntu.

### `Temporary failure in name resolution`

Сервер не имеет доступа в интернет. Проверь:
```bash
# На сервере
curl -I https://hub.docker.com
ping 8.8.8.8
```

Для VirtualBox: добавь второй адаптер типа **NAT** и подними интерфейс:
```bash
systemctl restart systemd-networkd
```

### `SSLError: UNEXPECTED_EOF_WHILE_READING`

Модуль не может подключиться к Management API с control node.
`ansible_host` должен быть IP-адресом, доступным с твоей машины — не внешним IP сервера если он недоступен.

### `Unable to find any of pip3 to use`

Модуль `outline_server` должен запускаться на control node, а не на сервере.
Убедись что в `configure.yml` присутствует `delegate_to: localhost`.

### `non-zero return code` при запуске установщика

Установщик Outline задаёт интерактивный вопрос об установке Docker.
В нашем playbook Docker устанавливается отдельно до запуска установщика, поэтому вопрос не должен появляться. Если проблема возникла — проверь что Docker установлен:
```bash
docker --version
```
