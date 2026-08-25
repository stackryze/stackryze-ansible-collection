# -*- coding: utf-8 -*-
# Shared helper for talking to the Stackryze DNS REST API.
from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json

from ansible.module_utils.urls import open_url
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError


def _strip(value):
    return value[:-1] if value and value.endswith(".") else value


class StackryzeError(Exception):
    pass


class StackryzeAPI(object):
    def __init__(self, api_url, token):
        self.base = (api_url or "https://api-dns.stackryze.com/api").rstrip("/")
        self.token = token

    def _request(self, method, path, payload=None):
        url = self.base + path
        headers = {
            "Authorization": "Bearer %s" % self.token,
            "Content-Type": "application/json",
        }
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        try:
            resp = open_url(url, method=method, headers=headers, data=data, timeout=20)
            body = resp.read()
        except HTTPError as e:
            body = e.read()
            try:
                parsed = json.loads(body.decode("utf-8"))
                message = parsed.get("error", body.decode("utf-8"))
            except Exception:
                message = body.decode("utf-8") if body else str(e)
            raise StackryzeError("%s %s failed (%s): %s" % (method, path, e.code, message))
        except URLError as e:
            raise StackryzeError("%s %s failed: %s" % (method, path, e))
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except ValueError:
            return {}

    def find_zone(self, name):
        data = self._request("GET", "/zones")
        zones = data.get("zones", data if isinstance(data, list) else [])
        target = _strip(name).lower()
        for zone in zones:
            if _strip(zone.get("name", "")).lower() == target:
                return {"id": zone.get("_id"), "name": _strip(zone.get("name", ""))}
        raise StackryzeError("zone %r not found on Stackryze" % name)

    # Returns a list of {name, type, content, ttl} for the zone.
    def list_records(self, zone_id):
        rrsets = self._request("GET", "/zones/%s/records?max=1000" % zone_id)
        out = []
        for rr in rrsets or []:
            for record in rr.get("records", []):
                if record.get("disabled"):
                    continue
                out.append({
                    "name": _strip(rr.get("name", "")),
                    "type": rr.get("type"),
                    "content": _strip(record.get("content", "")),
                    "ttl": rr.get("ttl"),
                })
        return out

    def add_record(self, zone_id, name, rtype, content, ttl):
        return self._request(
            "POST",
            "/zones/%s/records" % zone_id,
            {"type": rtype, "name": name, "content": content, "ttl": ttl},
        )

    def delete_record(self, zone_id, name, rtype, content):
        return self._request(
            "DELETE",
            "/zones/%s/records" % zone_id,
            {"type": rtype, "name": name, "content": content},
        )
