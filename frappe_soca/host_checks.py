"""Native acceptance fixture for a disposable site only. Run with bench execute.

This does not contact a provider or mark activation evidence.
"""
import tempfile
from pathlib import Path

import frappe
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from . import accounts, config
from .soca.errors import SocaError


def run():
    frappe.set_user("Administrator")
    checks = []
    with tempfile.TemporaryDirectory() as directory:
        key = ec.generate_private_key(ec.SECP256R1())
        path = Path(directory) / "private.pem"
        path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        path.chmod(0o600)
        profile = frappe.get_doc({"doctype": "SOCA Profile", "name": "host-test", "origin": "https://frappe.example.com", "issuer": "https://auth.resoauth.cloud", "private_key_file": str(path), "allow_domains": "example.com"})
        # A deployment transaction-key reference is required before activation.
        from cryptography.fernet import Fernet
        tx = Path(directory) / "transactions.key"
        tx.write_bytes(Fernet.generate_key())
        tx.chmod(0o600)
        frappe.conf.soca = {"transaction_key_file": str(tx)}
        profile.insert()
        candidate = config.load(profile.name)
        assert candidate.document()["token_endpoint_auth_signing_alg"] == "ES256"
        checks.append("native profile schema and ES256 metadata")
        if not frappe.db.exists("Role", "SOCA Website Test"):
            frappe.get_doc({"doctype": "Role", "role_name": "SOCA Website Test", "desk_access": 0}).insert()
        user = frappe.get_doc({"doctype": "User", "email": "existing-soca-host@example.com", "first_name": "Existing", "user_type": "Website User", "enabled": 1, "send_welcome_email": 0, "roles": [{"role": "SOCA Website Test"}]}).insert()
        claims = {"sub": "host-subject", "email": user.name, "email_verified": True}
        try:
            accounts.resolve(candidate, claims)
            raise AssertionError("Email-only account selection must fail")
        except SocaError:
            checks.append("verified email never auto-links existing account")
        frappe.get_doc({"doctype": "SOCA Identity", "issuer": candidate.issuer, "subject": claims["sub"], "user": user.name, "approval_reason": "Independently approved disposable native fixture"}).insert()
        assert accounts.resolve(candidate, claims).name == user.name
        checks.append("approved issuer and subject resolves exact eligible user")
        user.enabled = 0
        user.save()
        try:
            accounts.resolve(candidate, claims)
            raise AssertionError("Disabled account must fail")
        except SocaError:
            checks.append("disabled local account rejected")
        user.enabled = 1
        user.save()
        candidate.values.update(provision=True, provision_role="SOCA Website Test")
        claims.update(sub="new-host-subject", email="new-soca-host@example.com")
        created = accounts.resolve(candidate, claims)
        assert created.user_type == "Website User"
        assert "System Manager" not in frappe.get_roles(created.name)
        assert frappe.db.get_value("SOCA Identity", accounts.link_key(candidate.issuer, claims["sub"]), "user") == created.name
        checks.append("opt-in atomic low privilege website provisioning and identity link")
        # The disposable check deliberately rolls back all test account/configuration writes.
        frappe.db.rollback()
    return {"passed": len(checks), "checks": checks, "provider_login": "not attempted"}
