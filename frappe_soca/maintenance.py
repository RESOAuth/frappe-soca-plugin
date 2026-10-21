import frappe
from frappe.utils import now_datetime


def cleanup():
    frappe.db.delete("SOCA Transaction", {"expires_at": ("<", now_datetime())})
