import hashlib
import frappe
from frappe.utils import validate_email_address

from .soca.core import admission, profile_text
from .soca.errors import SocaError


def link_key(issuer, subject):
    return hashlib.sha256((issuer + "\0" + subject).encode()).hexdigest()


def eligible(name):
    user = frappe.get_doc("User", name)
    if not user.enabled or name in ("Administrator", "Guest") or "System Manager" in frappe.get_roles(user.name):
        raise SocaError("account_ineligible")
    return user


def resolve(config, claims):
    email = admission(config, claims)
    key = link_key(config.issuer, claims["sub"])
    # Serialise conflicting identity resolution with a unique native identity record.
    linked = frappe.db.get_value("SOCA Identity", key, "user")
    if linked:
        return eligible(linked)
    if not config.values.get("provision"):
        raise SocaError("protected_link_required")
    if frappe.db.exists("User", email):
        raise SocaError("existing_email_requires_approved_link")
    role = config.values.get("provision_role")
    if not role or role in ("System Manager", "Administrator", "All", "Guest") or frappe.db.get_value("Role", role, "desk_access"):
        raise SocaError("low_privilege_website_role_required")
    if not frappe.db.exists("Role", role):
        raise SocaError("provision_role_missing")
    validate_email_address(email, throw=True)
    frappe.db.savepoint("soca_provision")
    try:
        user = frappe.get_doc({"doctype": "User", "email": email, "enabled": 1,
                              "first_name": profile_text(claims, "given_name", "SOCA"),
                              "last_name": profile_text(claims, "family_name"),
                              "user_type": "Website User", "send_welcome_email": 0,
                              "roles": [{"role": role}]})
        user.flags.no_welcome_mail = True
        user.insert(ignore_permissions=True)
        # No local password is assigned. Host recovery remains independently controlled.
        link = frappe.get_doc({"doctype": "SOCA Identity", "issuer": config.issuer,
                               "subject": claims["sub"], "user": user.name,
                               "approval_reason": "Atomic opt-in SOCA website provisioning"})
        link.flags.soca_provisioning = True
        link.insert(ignore_permissions=True)
        return eligible(user.name)
    except Exception:
        frappe.db.rollback(save_point="soca_provision")
        raise SocaError("provisioning_failed") from None
