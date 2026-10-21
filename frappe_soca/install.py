import frappe


def after_install():
    # Schema and ACLs are installed through native DocType synchronisation.
    frappe.clear_cache()


def before_uninstall():
    frappe.db.delete("SOCA Transaction")
    # Identity links are security records. Export them before uninstalling the app.
    frappe.db.commit()
