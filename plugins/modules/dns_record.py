#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: dns_record
short_description: Manage DNS records on Stackryze DNS
version_added: "0.1.0"
description:
  - Create or delete a single DNS record in a zone on Stackryze DNS (dns.stackryze.com).
options:
  api_token:
    description:
      - API token with write scope. May also be set via the C(STACKRYZE_API_TOKEN) environment variable.
    type: str
    required: false
  api_url:
    description:
      - API base URL (include C(/api)).
    type: str
    default: https://api-dns.stackryze.com/api
  zone:
    description:
      - The zone name (e.g. C(example.com)). Must already exist on Stackryze.
    type: str
    required: true
  name:
    description:
      - Record label relative to the zone. Use C(@) for the apex.
    type: str
    default: "@"
  type:
    description:
      - Record type.
    type: str
    required: true
    choices: [A, AAAA, CNAME, MX, TXT, SRV, CAA]
  content:
    description:
      - Record value. For MX/SRV include priority, e.g. C(10 mail.example.com).
    type: str
    required: true
  ttl:
    description:
      - TTL in seconds (minimum 3600).
    type: int
    default: 3600
  state:
    description:
      - Whether the record should be present or absent.
    type: str
    default: present
    choices: [present, absent]
author:
  - Stackryze
"""

EXAMPLES = r"""
- name: Create an apex A record
  stackryze.dns.dns_record:
    zone: example.com
    name: "@"
    type: A
    content: 93.184.216.34

- name: Ensure a www CNAME
  stackryze.dns.dns_record:
    zone: example.com
    name: www
    type: CNAME
    content: example.com

- name: Remove a TXT record
  stackryze.dns.dns_record:
    zone: example.com
    name: _verify
    type: TXT
    content: "token-123"
    state: absent
"""

RETURN = r"""
record:
  description: The record that was ensured.
  type: dict
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule, env_fallback
from ansible_collections.stackryze.dns.plugins.module_utils.stackryze import (
    StackryzeAPI,
    StackryzeError,
)


def _strip(value):
    return value[:-1] if value and value.endswith(".") else value


def _norm_txt(content):
    # Compare TXT values regardless of surrounding quotes.
    return content[1:-1] if len(content) >= 2 and content.startswith('"') and content.endswith('"') else content


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            api_token=dict(type="str", required=False, no_log=True, fallback=(env_fallback, ["STACKRYZE_API_TOKEN"])),
            api_url=dict(type="str", default="https://api-dns.stackryze.com/api", fallback=(env_fallback, ["STACKRYZE_API_URL"])),
            zone=dict(type="str", required=True),
            name=dict(type="str", default="@"),
            type=dict(type="str", required=True, choices=["A", "AAAA", "CNAME", "MX", "TXT", "SRV", "CAA"]),
            content=dict(type="str", required=True),
            ttl=dict(type="int", default=3600),
            state=dict(type="str", default="present", choices=["present", "absent"]),
        ),
        supports_check_mode=True,
    )

    params = module.params
    if not params["api_token"]:
        module.fail_json(msg="api_token is required (or set STACKRYZE_API_TOKEN)")

    ttl = params["ttl"] if params["ttl"] and params["ttl"] >= 3600 else 3600
    rtype = params["type"]
    label = params["name"] or "@"
    content = params["content"]
    # Send TXT content quoted; compare unquoted.
    send_content = '"%s"' % content if rtype == "TXT" and not content.startswith('"') else content
    cmp_content = _norm_txt(content)

    api = StackryzeAPI(params["api_url"], params["api_token"])
    result = dict(changed=False, record=dict(zone=params["zone"], name=label, type=rtype, content=content, ttl=ttl))

    try:
        zone = api.find_zone(params["zone"])
        expected_fqdn = _strip(zone["name"]) if label == "@" else "%s.%s" % (label, _strip(zone["name"]))
        existing = api.list_records(zone["id"])

        found = None
        for rec in existing:
            if rec["type"] != rtype:
                continue
            if rec["name"].lower() != expected_fqdn.lower():
                continue
            if _norm_txt(rec["content"]) == cmp_content:
                found = rec
                break

        if params["state"] == "present":
            if found:
                module.exit_json(**result)
            result["changed"] = True
            if not module.check_mode:
                api.add_record(zone["id"], label, rtype, send_content, ttl)
            module.exit_json(**result)
        else:  # absent
            if not found:
                module.exit_json(**result)
            result["changed"] = True
            if not module.check_mode:
                api.delete_record(zone["id"], label, rtype, send_content)
            module.exit_json(**result)
    except StackryzeError as e:
        module.fail_json(msg=str(e), **result)


def main():
    run_module()


if __name__ == "__main__":
    main()
