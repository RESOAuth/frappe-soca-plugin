import os
import frappe

from .soca.core import Config
from .soca.errors import SocaError

FIELDS = ("origin", "issuer", "metadata_mode", "proxy", "private_key_file", "allow_emails", "deny_emails", "allow_domains", "deny_domains", "provision", "provision_role", "enabled", "client_name", "client_uri", "logo_uri", "policy_uri", "tos_uri", "id_token_alg", "max_age", "required_amr", "acr_values", "userinfo")
LIST_FIELDS = {"allow_emails", "deny_emails", "allow_domains", "deny_domains", "required_amr", "acr_values"}


def deployment():
    value = frappe.conf.get("soca", {})
    if not isinstance(value, dict):
        raise SocaError("invalid_site_configuration")
    return value


def raw_values(name, doc=None):
    doc = doc or frappe.get_doc("SOCA Profile", name)
    values = {}
    for key in FIELDS:
        value = doc.get(key)
        if key in LIST_FIELDS:
            value = [part.strip() for part in (value or "").splitlines() if part.strip()]
        if key in ("enabled", "provision", "userinfo"):
            value = bool(value)
        if value is not None and value != "":
            values[key] = value
    # Deployment values are applied last and cannot be weakened through the database/UI.
    values.update(deployment().get("profiles", {}).get(name, {}))
    values["emergency_disabled"] = bool(deployment().get("emergency_disabled", False))
    return values


def load(name, doc=None):
    route = "/api/method/frappe_soca.api."
    routes = {key: route + key + "?profile=" + name for key in ("callback", "metadata", "jwks")}
    website = frappe.get_single("Website Settings")
    title = website.get("app_name") or website.get("brand_html") or frappe.conf.get("app_name") or "Frappe"
    # HTML branding is never exposed as client_name.
    if "<" in title:
        title = "Frappe"
    return Config.load(name, raw_values(name, doc), routes, application_name=title)


def transaction_key_file():
    path = os.getenv("SOCA_TRANSACTION_KEY_FILE") or deployment().get("transaction_key_file")
    if not path:
        raise SocaError("transaction_key_file_required")
    return path


def evidence(name):
    doc = frappe.get_doc("SOCA Profile", name)
    return {"document": doc.document_evidence, "login": doc.login_evidence}
