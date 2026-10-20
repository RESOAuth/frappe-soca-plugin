import frappe
from frappe.model.document import Document
from frappe_soca.accounts import eligible, link_key
from frappe_soca.soca.transport import validate_url


class SOCAIdentity(Document):
    def autoname(self):
        self.identity_key = link_key(self.issuer, self.subject)
        self.name = self.identity_key

    def validate(self):
        if not self.flags.soca_provisioning and "System Manager" not in frappe.get_roles():
            frappe.throw("Audited administrator approval required", frappe.PermissionError)
        validate_url(self.issuer)
        if not isinstance(self.subject, str) or not 1 <= len(self.subject) <= 255 or not self.approval_reason:
            frappe.throw("Exact issuer/subject and an approval reason are required")
        eligible(self.user)
        if not self.is_new():
            previous = self.get_doc_before_save()
            if previous and any(previous.get(key) != self.get(key) for key in ("issuer", "subject", "user")):
                frappe.throw("Identity migration requires unlinking with an audit reason and creating a new approval")
