# Stackryze DNS Ansible Collection (`stackryze.dns`)

Manage DNS records on [Stackryze DNS](https://dns.stackryze.com) from Ansible.
The collection is dependency-free (uses Ansible's built-in HTTP client) and talks
to the Stackryze REST API with a Bearer token — no impact on the DNS serving path.

## Install

```bash
# From a built tarball
ansible-galaxy collection build
ansible-galaxy collection install stackryze-dns-0.1.0.tar.gz
```

## Authentication

Create an API token with **write** scope (Settings → API tokens), then either
pass `api_token:` or export it:

```bash
export STACKRYZE_API_TOKEN=sk_dns_xxxxxxxx
# optional: export STACKRYZE_API_URL=https://api.stackryze.com/api
```

## Modules

### `stackryze.dns.dns_record`

Idempotently create or delete a single record.

| Option | Required | Default | Notes |
|--------|----------|---------|-------|
| `api_token` | no | env `STACKRYZE_API_TOKEN` | Write-scope token |
| `api_url` | no | `https://api.stackryze.com/api` | Or env `STACKRYZE_API_URL` |
| `zone` | yes | — | Zone name; must exist on Stackryze |
| `name` | no | `@` | Label relative to the zone |
| `type` | yes | — | A, AAAA, CNAME, MX, TXT, SRV, CAA |
| `content` | yes | — | For MX/SRV include priority (`10 mail.example.com`) |
| `ttl` | no | `3600` | Minimum 3600s |
| `state` | no | `present` | `present` or `absent` |

Supports `--check` mode.

## Example

```yaml
- hosts: localhost
  tasks:
    - stackryze.dns.dns_record:
        zone: example.com
        name: www
        type: CNAME
        content: example.com
```

See [playbooks/example.yml](playbooks/example.yml).

## Notes

- Zones must already exist on Stackryze (creation requires verification in the
  dashboard). This collection manages records.
- TXT values are compared regardless of surrounding quotes, so runs are idempotent.
