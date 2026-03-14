# ansible-outline-deploy

[![CI](https://img.shields.io/github/actions/workflow/status/Zeph1rr/ansible-outline/tests.yml?style=plastic&label=lint)](https://github.com/zeph1rr/ansible-outline/actions/workflows/lint.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

IaC tool for deploying and managing [Outline VPN](https://getoutline.org/) servers via Ansible.

Describe your servers in a single YAML file and deploy Outline across your entire infrastructure with one command.

📖 **Documentation:** [English](docs/en.md) | [Русский](docs/ru.md)

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/zeph1rr/ansible-outline-deploy.git
cd ansible-outline-deploy

# 2. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Create inventory
cp inventory/hosts.yml.example inventory/hosts.yml
$EDITOR inventory/hosts.yml

# 4. Test connectivity
ansible vpn_servers -i inventory/hosts.yml -m ping

# 5. Deploy
ansible-playbook -i inventory/hosts.yml playbook.yml
```

> **Windows users:** Ansible requires [WSL](https://learn.microsoft.com/en-us/windows/wsl/install).
> Run all commands from the Ubuntu terminal.

---

## Commands

| Command | Description |
|---|---|
| `ansible-playbook playbook.yml` | Full deploy: install + configure |
| `ansible-playbook playbook.yml --skip-tags install` | Configure only (Outline already installed) |
| `ansible-playbook playbook.yml --limit my-server` | Single host |
| `ansible-playbook playbook.yml --check --diff` | Dry-run |
| `ansible-playbook uninstall.yml` | Uninstall Outline from all servers |
| `ansible-playbook uninstall.yml --limit my-server` | Uninstall from a single server |

---

## Project structure

```
ansible-outline-deploy/
├── docs/
│   ├── en.md                       # Full documentation (English)
│   └── ru.md                       # Full documentation (Russian)
├── inventory/
│   ├── hosts.yml                   # Your inventory (git-ignored)
│   ├── hosts.yml.example           # Template — copy and fill in
│   └── facts/                      # Auto-generated management URLs (git-ignored)
├── roles/
│   └── outline/
│       ├── defaults/main.yml       # Default variable values
│       ├── files/
│       │   └── get_outline_str.sh  # Server utility to view management_url
│       ├── library/
│       │   └── outline_server.py   # Custom Ansible module for Outline API
│       └── tasks/
│           ├── main.yml
│           ├── install.yml         # Docker + Outline installation (tag: install)
│           └── configure.yml       # API configuration
├── .github/workflows/ci.yml        # Syntax check on every push/PR
├── ansible.cfg
├── playbook.yml                    # Deploy
├── requirements.txt
└── uninstall.yml                   # Uninstall
```

---

## License

[MIT](LICENSE) © zeph1rr
