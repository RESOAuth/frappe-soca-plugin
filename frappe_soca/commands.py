"""Headless operations: bench --site SITE execute frappe_soca.commands.check."""
import frappe
from . import config
from .soca import core


def status(profile):
    candidate = config.load(profile)
    return {"revision": candidate.fingerprint, "client_id": candidate.client_id, "evidence": config.evidence(profile), "sources": "site_config > SOCA Profile"}


def check(profile):
    candidate = config.load(profile)
    proof = core.document_check(candidate)
    frappe.db.set_value("SOCA Profile", profile, {"document_evidence": proof, "login_evidence": ""}, update_modified=False)
    frappe.db.commit()
    return {"document": "passed", "revision": proof}


def disable(profile):
    frappe.db.set_value("SOCA Profile", profile, "enabled", 0)
    frappe.db.delete("SOCA Transaction", {"profile": profile})
    frappe.db.commit()
