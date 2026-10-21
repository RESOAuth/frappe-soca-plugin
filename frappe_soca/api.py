"""Frappe-native routes. Codes, state and token responses are never logged."""
import re
import secrets
from datetime import timedelta

import frappe
from frappe.utils import now_datetime

from . import accounts, config
from .soca import core
from .soca.errors import SocaError

COOKIE = "soca_browser"


def operator():
    if frappe.session.user == "Guest" or "System Manager" not in frappe.get_roles():
        frappe.throw("System Manager access required", frappe.PermissionError)
    return frappe.session.user


def reply(document):
    from werkzeug.wrappers import Response
    return Response(core.canonical(document), content_type="application/json", headers={"Cache-Control": "public, max-age=60", "X-Content-Type-Options": "nosniff"})


def redirect(url):
    frappe.local.response.update(type="redirect", location=url)


def fail(error):
    reference = secrets.token_hex(6)
    # Fixed codes only; never log callback arguments or a raw exception.
    frappe.logger("soca").warning("SOCA login rejected [%s] %s", reference, type(error).__name__)
    frappe.local.response.http_status_code = 403
    return {"error": "SOCA sign-in could not be completed", "reference": reference}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def metadata(profile: str):
    return reply(config.load(profile).document())


@frappe.whitelist(allow_guest=True, methods=["GET"])
def jwks(profile: str):
    return reply({"keys": [config.load(profile).public_key]})


@frappe.whitelist(allow_guest=True, methods=["GET"])
def providers():
    result = []
    for name in frappe.get_all("SOCA Profile", pluck="name"):
        try:
            candidate = config.load(name)
            candidate.require_available(config.evidence(name))
            result.append({"label": candidate.values["client_name"], "url": "/api/method/frappe_soca.api.login?profile=" + name})
        except (SocaError, ValueError, OSError):
            continue
    return result


@frappe.whitelist(methods=["POST"])
def check(profile: str):
    operator()
    candidate = config.load(profile)
    if candidate.values.get("emergency_disabled"):
        raise SocaError("emergency_disabled")
    proof = core.document_check(candidate)
    frappe.db.set_value("SOCA Profile", profile, {"document_evidence": proof, "login_evidence": ""}, update_modified=False)
    return {"document": "passed", "revision": proof, "login": "not yet tested"}


@frappe.whitelist(methods=["POST"])
def test_login(profile: str):
    who = operator()
    return _begin(profile, test_operator=who)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def login(profile: str):
    try:
        return _begin(profile)
    except (SocaError, ValueError, OSError) as exc:
        return fail(exc)


def _begin(profile, test_operator=None):
    if frappe.request.scheme != "https":
        raise SocaError("https_required")
    candidate = config.load(profile)
    candidate.require_available(config.evidence(profile), test=test_operator is not None)
    browser = frappe.request.cookies.get(COOKIE)
    if not browser or not re.fullmatch(r"[A-Za-z0-9_-]{43}", browser):
        browser = secrets.token_urlsafe(32)
    # Frappe's anonymous sid is literally Guest, so a dedicated short-lived
    # HttpOnly binding cookie is necessary. It carries no verifier/state/claims.
    frappe.local.cookie_manager.set_cookie(COOKIE, browser, secure=True, httponly=True, samesite="Lax", max_age=300)
    state, payload, url = core.start(candidate, browser, test_operator=test_operator)
    frappe.get_doc({"doctype": "SOCA Transaction", "name": core.digest(state),
                    "profile": profile, "ciphertext": core.seal(payload, config.transaction_key_file()),
                    "expires_at": now_datetime() + timedelta(seconds=300)}).insert(ignore_permissions=True)
    if test_operator:
        return {"url": url}
    redirect(url)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def callback(profile: str, state: str = "", code: str = "", iss: str | None = None, error: str | None = None):
    try:
        if frappe.request.scheme != "https":
            raise SocaError("https_required")
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", state):
            raise SocaError("invalid_state")
        # A separate short transaction makes consumption durable even when
        # authentication/account work fails and the request rolls back.
        key = core.digest(state)
        rows = frappe.db.sql("SELECT ciphertext, profile FROM `tabSOCA Transaction` WHERE name=%s AND expires_at > %s FOR UPDATE", (key, now_datetime()), as_dict=True)
        if not rows or rows[0].profile != profile:
            raise SocaError("unknown_transaction")
        frappe.db.delete("SOCA Transaction", {"name": key})
        frappe.db.commit()
        candidate = config.load(profile)
        payload = core.unseal(rows[0].ciphertext, config.transaction_key_file())
        candidate.require_available(config.evidence(profile), test=payload.get("operator") is not None)
        core.validate_transaction(candidate, payload, frappe.request.cookies.get(COOKIE, ""), current_operator=frappe.session.user)
        if error:
            raise SocaError("provider_cancelled")
        claims = core.exchange(candidate, payload, code, iss)
        core.admission(candidate, claims)
        if payload.get("operator") is not None:
            operator()
            # No identity/account/profile/session writes in a candidate test.
            frappe.db.set_value("SOCA Profile", profile, "login_evidence", candidate.fingerprint, update_modified=False)
            redirect("/app/soca-profile/" + profile)
            return
        user = accounts.resolve(candidate, claims)
        # Native post_login rotates the authenticated sid and runs account hooks.
        frappe.local.login_manager.login_as(user.name)
        redirect(payload["return_to"])
    except (SocaError, ValueError, OSError) as exc:
        frappe.db.rollback()
        return fail(exc)


@frappe.whitelist(methods=["POST"])
def status(profile: str):
    operator()
    candidate = config.load(profile)
    return {"revision": candidate.fingerprint, "source": "site_config overrides database", "deployment_locks": list(config.deployment().get("profiles", {}).get(profile, {})), "client_id": candidate.client_id, "evidence": config.evidence(profile), "emergency_disabled": candidate.values.get("emergency_disabled", False)}
