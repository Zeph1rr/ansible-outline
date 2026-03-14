# ansible-outline-deploy Documentation

## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Inventory Configuration](#inventory-configuration)
4. [Commands](#commands)
5. [How management_url works](#how-management_url-works)
6. [Custom module outline_server](#custom-module-outline_server)
7. [get_outline_str utility](#get_outline_str-utility)
8. [Idempotency](#idempotency)
9. [Security](#security)
10. [Troubleshooting](#troubleshooting)

---

## Requirements

**Control node** (machine running Ansible):
- Python 3.12+
- Linux or macOS (Windows — WSL only)
- Network access to managed servers via SSH
- Network access to Outline Management API port

**Managed nodes** (servers where Outline is deployed):
- Ubuntu 22.04 or 24.04
- Internet access (to download Docker and Outline images)
- SSH access from the control node

> **Windows users:** Ansible does not support Windows as a control node.
> Install [WSL](https://learn.microsoft.com/en-us/windows/wsl/install), open an Ubuntu
> terminal and work from there. Your SSH key path will look like
> `/mnt/c/Users/<user>/.ssh/id_rsa`.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/zeph1rr/ansible-outline-deploy.git
cd ansible-outline-deploy
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create your inventory

```bash
cp inventory/hosts.yml.example inventory/hosts.yml
```

Edit `inventory/hosts.yml` and add your servers.

### 4. Test connectivity

```bash
ansible vpn_servers -i inventory/hosts.yml -m ping
```

Expected response for each host:
```
my-server | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

---

## Inventory Configuration

All settings live in a single file: `inventory/hosts.yml`.
Use `inventory/hosts.yml.example` as a starting point.

### File structure

```yaml
all:
  children:
    vpn_servers:
      vars:
        # SSH — applied to all hosts in the group
        ansible_user: root
        ansible_ssh_private_key_file: ~/.ssh/id_rsa
        ansible_python_interpreter: /usr/bin/python3

        # Outline defaults for the whole group
        outline_server_name: "Outline VPN"
        outline_metrics_enabled: false
        outline_default_port: ~          # ~ = leave unchanged
        outline_default_limit_bytes: ~   # ~ = leave unchanged; 0 = remove limit
        outline_hostname: ~              # ~ = use server IP

      hosts:
        my-server-1:
          ansible_host: 1.2.3.4
          outline_server_name: "EU Node 1"

        my-server-2:
          ansible_host: 5.6.7.8
          outline_server_name: "EU Node 2"
          outline_default_limit_bytes: 53687091200   # 50 GB
```

### SSH variable reference

| Variable | Description | Example |
|---|---|---|
| `ansible_host` | Server IP or DNS name | `1.2.3.4` |
| `ansible_user` | SSH user | `root` |
| `ansible_port` | SSH port | `2222` (default `22`) |
| `ansible_ssh_private_key_file` | Path to private SSH key | `~/.ssh/id_rsa` |
| `ansible_ssh_pass` | SSH password (alternative to key) | `s3cr3t` |
| `ansible_python_interpreter` | Path to Python on the server | `/usr/bin/python3` |

### Outline variable reference

| Variable | Description | Default |
|---|---|---|
| `outline_server_name` | Display name of the server | `"Outline VPN"` |
| `outline_hostname` | Hostname used in access key URLs (`ss://`) | `~` — server IP |
| `outline_default_port` | Default port for new access keys | `~` — leave unchanged |
| `outline_default_limit_bytes` | Data transfer limit in bytes; `0` = remove limit | `~` — leave unchanged |
| `outline_metrics_enabled` | Share anonymous metrics with Jigsaw | `false` |
| `outline_management_url` | Management API URL (auto-populated) | `~` |

### Variable precedence

Host-level variables override group `vars`. This allows setting shared defaults in `vars`
and overriding them per server.

### Host configuration examples

**Minimal** — only IP, everything else from `vars`:
```yaml
my-server:
  ansible_host: 1.2.3.4
  outline_server_name: "EU Node"
```

**Password auth with non-standard SSH port:**
```yaml
my-server:
  ansible_host: 5.6.7.8
  ansible_port: 2222
  ansible_user: ubuntu
  ansible_ssh_pass: "s3cr3t"
  outline_server_name: "EU Node"
```

**Custom hostname and data limit:**
```yaml
my-server:
  ansible_host: 9.10.11.12
  outline_server_name: "EU Node"
  outline_hostname: "vpn.mycompany.com"
  outline_default_port: 8388
  outline_default_limit_bytes: 53687091200   # 50 GB
  outline_metrics_enabled: true
```

**Already installed** — management_url set manually:
```yaml
my-server:
  ansible_host: 11.22.33.44
  outline_management_url: "https://11.22.33.44:12345/AbCdEfGhIj"
  outline_server_name: "EU Node"
```

---

## Commands

### Full deploy

Install Docker + Outline + apply configuration:

```bash
ansible-playbook -i inventory/hosts.yml playbook.yml
```

### Configure only

Outline is already installed, only settings need to change.
Edit the relevant variables in `hosts.yml`, then run:

```bash
ansible-playbook -i inventory/hosts.yml playbook.yml --skip-tags install
```

### Single host

```bash
ansible-playbook -i inventory/hosts.yml playbook.yml --limit my-server
```

### Dry-run

Preview changes without applying them:

```bash
ansible-playbook -i inventory/hosts.yml playbook.yml --check --diff
```

### Uninstall

> ⚠️ Destructive operation. All Outline data (keys, settings) will be permanently deleted.

```bash
# All servers
ansible-playbook -i inventory/hosts.yml uninstall.yml

# Single server
ansible-playbook -i inventory/hosts.yml uninstall.yml --limit my-server

# Dry-run
ansible-playbook -i inventory/hosts.yml uninstall.yml --check
```

The uninstall playbook:
1. Prompts for confirmation (Enter to continue, Ctrl+C to abort)
2. Stops and removes Docker containers `shadowbox` and `watchtower`
3. Removes Outline Docker images
4. Removes `/opt/outline` directory and `get_outline_str` utility
5. Removes `inventory/facts/<hostname>.yml` on the control node

After uninstall the host remains in `inventory/hosts.yml` — redeploy at any time with
`ansible-playbook playbook.yml --limit my-server`.

---

## How management_url works

Outline generates a unique Management API URL on installation and writes it to
`/opt/outline/access.txt` on the server.

```
First playbook run:
  1. SSH → install Docker and Outline
  2. Read /opt/outline/access.txt from the server
  3. Replace external IP with ansible_host in the URL
  4. Update access.txt on the server
  5. Save URL to inventory/facts/<hostname>.yml on the control node

Subsequent runs:
  1. pre_tasks loads inventory/facts/<hostname>.yml
  2. management_url is already known
  3. --skip-tags install applies only API configuration
```

`inventory/facts/` files contain the Management API access token.
They are excluded from git via `.gitignore`.

For **private** repositories — you can commit the facts or encrypt them:
```bash
ansible-vault encrypt inventory/facts/my-server.yml
# add the flag when running:
ansible-playbook playbook.yml --ask-vault-pass
```

---

## Custom module outline_server

File: `roles/outline/library/outline_server.py`

The module uses [outline-vpn-api-client](https://github.com/Zeph1rr/outline-vpn-api-client)
to configure the server through the Management API.

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `management_url` | str | Management API URL (required) |
| `server_name` | str | New server name |
| `hostname` | str | Hostname for access key URLs |
| `default_port` | int | Port for new access keys |
| `default_limit_bytes` | int | Data limit in bytes; `0` = remove limit |
| `metrics_enabled` | bool | Enable anonymous metrics |

### Return values

| Field | Description |
|---|---|
| `changed` | `true` if at least one setting was updated |
| `server_id` | Unique server identifier |
| `server_name` | Server name after changes |
| `changes` | List of applied changes |

### Behaviour

- **Idempotent**: compares current state with desired, calls API only on mismatch
- **Supports `--check`**: in dry-run mode reports what would change without applying it
- **Runs on control node** (`delegate_to: localhost`) — SSH to servers is only needed for installation

---

## get_outline_str utility

After deployment, the command `get_outline_str` is available on every server.

```bash
root@my-server:~# get_outline_str
{"apiUrl":"https://1.2.3.4:12345/AbCdEfGhIj","certSha256":"B818...661E3"}
```

Outputs the `management_url` and `certSha256` — everything needed to connect Outline Manager.

Source: `roles/outline/files/get_outline_str.sh`
Installed to: `/usr/local/bin/get_outline_str`

---

## Idempotency

Re-running the playbook is safe — Ansible checks the current state before every action.

| Situation | Behaviour |
|---|---|
| Docker is already installed | Docker install steps are skipped (`changed=false`) |
| Outline is already installed | `install_server.sh` is not re-run (checks for `/opt/outline/access.txt`) |
| Server settings match inventory | Module returns `changed=false`, API is not called |
| `outline_default_limit_bytes: 0` | Data limit is **removed** from the server |
| Parameter is `~` (null) | Current value on the server is **left untouched** |

---

## Security

### What not to commit to a public repository

`.gitignore` already excludes:
- `inventory/hosts.yml` — contains IP addresses, usernames, passwords
- `inventory/facts/` — contains Management API URL with access token

### SSH keys

Use SSH keys instead of passwords wherever possible:
```bash
ssh-keygen -t ed25519 -C "ansible-outline"
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@your-server
```

Then in `hosts.yml`:
```yaml
ansible_ssh_private_key_file: ~/.ssh/id_ed25519
```

### ansible-vault

For storing passwords and tokens encrypted:
```bash
# Encrypt a facts file
ansible-vault encrypt inventory/facts/my-server.yml

# Encrypt a single variable in hosts.yml
ansible-vault encrypt_string 's3cr3t' --name 'ansible_ssh_pass'

# Run with decryption
ansible-playbook playbook.yml --ask-vault-pass
# or using a password file
ansible-playbook playbook.yml --vault-password-file ~/.vault_pass
```

---

## Troubleshooting

### `ansible.cfg` ignored (world-writable directory)

```
[WARNING]: Ansible is being run in a world writable directory, ignoring it as an ansible.cfg source.
```

The directory has overly permissive rights. Fix:
```bash
chmod 755 /path/to/ansible-outline-deploy
```

### `[WinError 1] Incorrect function`

Ansible does not run natively on Windows. Install WSL:
```powershell
wsl --install
```
Then work from the Ubuntu terminal.

### `Temporary failure in name resolution`

The server has no internet access. Check:
```bash
# On the server
curl -I https://hub.docker.com
ping 8.8.8.8
```

For VirtualBox: add a second **NAT** adapter and bring up the interface:
```bash
systemctl restart systemd-networkd
```

### `SSLError: UNEXPECTED_EOF_WHILE_READING`

The module cannot reach the Management API from the control node.
`ansible_host` must be an IP reachable from your machine — not an external IP if it is behind NAT.

### `Unable to find any of pip3 to use`

The `outline_server` module must run on the control node, not on the server.
Make sure `delegate_to: localhost` is present in `configure.yml`.

### `non-zero return code` when running the installer

The Outline installer asks an interactive question about installing Docker.
In this playbook Docker is installed separately before the installer runs, so the prompt
should not appear. If it does, verify Docker is installed:
```bash
docker --version
```
