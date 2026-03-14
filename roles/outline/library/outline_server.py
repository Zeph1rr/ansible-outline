#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = r"""
---
module: outline_server
short_description: Configure an Outline VPN server via its management API
description:
  - Connects to the Outline management API and applies the desired
    server configuration (name, hostname, port, data limit, metrics).
  - Fully idempotent — only makes API calls when the current state
    differs from the desired state.
  - Reports C(changed=true) only when at least one setting was updated.
options:
  management_url:
    description: Outline management API URL (from access.txt).
    required: true
    type: str
  server_name:
    description: Display name of the server.
    type: str
  hostname:
    description: Hostname advertised in access keys (ss:// URLs).
    type: str
  default_port:
    description: Default port for newly created access keys.
    type: int
  default_limit_bytes:
    description:
      - Server-wide data transfer limit in bytes.
      - Set to 0 to remove the limit.
      - Omit to leave the current value unchanged.
    type: int
  metrics_enabled:
    description: Whether to share anonymous metrics with Jigsaw.
    type: bool
    default: false
requirements:
  - outline-vpn-api-client >= 1.1
author:
  - outline_deploy
"""

EXAMPLES = r"""
- name: Configure Outline server
  outline_server:
    management_url: "https://1.2.3.4:12345/AbCdEf"
    server_name: "EU Node"
    hostname: "vpn.example.com"
    default_port: 8388
    default_limit_bytes: 53687091200   # 50 GB
    metrics_enabled: false

- name: Remove server-wide data limit
  outline_server:
    management_url: "https://1.2.3.4:12345/AbCdEf"
    default_limit_bytes: 0
"""

RETURN = r"""
server_id:
  description: Unique server identifier.
  returned: always
  type: str
server_name:
  description: Current server name after any changes.
  returned: always
  type: str
changes:
  description: List of settings that were updated.
  returned: always
  type: list
  elements: str
"""

import traceback
import warnings

from ansible.module_utils.basic import AnsibleModule

try:
    from outline_vpn_api_client import OutlineClient
    from outline_vpn_api_client.error import ResponseNotOkException
    HAS_OUTLINE_CLIENT = True
except ImportError:
    HAS_OUTLINE_CLIENT = False


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            management_url   = dict(type="str",  required=True, no_log=True),
            server_name      = dict(type="str",  required=False, default=None),
            hostname         = dict(type="str",  required=False, default=None),
            default_port     = dict(type="int",  required=False, default=None),
            default_limit_bytes = dict(type="int", required=False, default=None),
            metrics_enabled  = dict(type="bool", required=False, default=None),
        ),
        supports_check_mode=True,
    )

    if not HAS_OUTLINE_CLIENT:
        module.fail_json(
            msg="outline-vpn-api-client is required: pip install outline-vpn-api-client"
        )

    p = module.params
    changes = []

    # ── Connect ──────────────────────────────────────────────────────
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        client = OutlineClient(management_url=p["management_url"], ssl_verify=False)

    try:
        info = client.server.get_information()
    except ResponseNotOkException as e:
        module.fail_json(msg=f"Cannot reach Outline API: {e}")
    except Exception as e:
        module.fail_json(msg=f"Unexpected error connecting to API: {e}\n{traceback.format_exc()}")

    # ── Diff helpers ─────────────────────────────────────────────────
    def _apply(label, current, desired, apply_fn):
        """Call apply_fn only when desired != current. Records the change."""
        if desired is None:
            return   # parameter not set → leave untouched
        if current == desired:
            return   # already correct
        changes.append(label)
        if not module.check_mode:
            try:
                apply_fn()
            except ResponseNotOkException as e:
                module.fail_json(msg=f"Failed to {label}: {e}")

    # ── server_name ──────────────────────────────────────────────────
    _apply(
        f"rename server to '{p['server_name']}'",
        info.name,
        p["server_name"],
        lambda: client.server.rename(p["server_name"]),
    )

    # ── hostname ─────────────────────────────────────────────────────
    _apply(
        f"set hostname to '{p['hostname']}'",
        info.hostnameForAccessKeys,
        p["hostname"],
        lambda: client.server.change_hostname(p["hostname"]),
    )

    # ── default_port ─────────────────────────────────────────────────
    _apply(
        f"set default port to {p['default_port']}",
        info.portForNewAccessKeys,
        p["default_port"],
        lambda: client.server.change_default_port_for_new_keys(p["default_port"]),
    )

    # ── default_limit_bytes ──────────────────────────────────────────
    if p["default_limit_bytes"] is not None:
        current_limit = info.accessKeyDataLimit.bytes if info.accessKeyDataLimit else 0
        desired_limit = p["default_limit_bytes"]
        if current_limit != desired_limit:
            changes.append(
                "remove server data limit" if desired_limit == 0
                else f"set server data limit to {desired_limit} bytes"
            )
            if not module.check_mode:
                try:
                    if desired_limit == 0:
                        client.server.remove_server_default_limits()
                    else:
                        client.server.set_server_default_limits(desired_limit)
                except ResponseNotOkException as e:
                    module.fail_json(msg=f"Failed to update data limit: {e}")

    # ── metrics_enabled ──────────────────────────────────────────────
    _apply(
        f"set metrics_enabled={p['metrics_enabled']}",
        info.metricsEnabled,
        p["metrics_enabled"],
        lambda: client.metrics.change_enabled_state(p["metrics_enabled"]),
    )

    # ── Result ───────────────────────────────────────────────────────
    # Re-fetch name in case it was just changed (check_mode: use desired)
    final_name = p["server_name"] if p["server_name"] and changes else info.name

    module.exit_json(
        changed=bool(changes),
        server_id=info.serverId,
        server_name=final_name,
        changes=changes,
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
