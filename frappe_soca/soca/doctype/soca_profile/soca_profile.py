import frappe
from frappe.model.document import Document
from frappe_soca import config
from frappe_soca.soca.core import secret_file


class SOCAProfile(Document):
    def validate(self):
        previous = self.get_doc_before_save()
        if not previous and (self.document_evidence or self.login_evidence) or previous and (self.document_evidence != previous.document_evidence or self.login_evidence != previous.login_evidence):
            frappe.throw("Document and login evidence can only be recorded by SOCA checks")
        candidate = config.load(self.name, self)
        secret_file(config.transaction_key_file())
        if self.enabled:
            candidate.require_available({"document": self.document_evidence, "login": self.login_evidence})
        if previous and config.load(self.name, previous).fingerprint != candidate.fingerprint:
            self.document_evidence = self.login_evidence = ""
        # Deployment locks are enforced through effective configuration on every use.

    def on_trash(self):
        frappe.db.delete("SOCA Transaction", {"profile": self.name})
