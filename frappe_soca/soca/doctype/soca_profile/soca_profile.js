frappe.ui.form.on("SOCA Profile", {
  refresh(frm) {
    frm.add_custom_button("Check public documents", async () => {
      const r = await frappe.call({method: "frappe_soca.api.check", args: {profile: frm.doc.name}});
      frappe.msgprint("Public documents checked. A real test login is still required.");
      await frm.reload_doc();
    });
    frm.add_custom_button("Test candidate login", async () => {
      const r = await frappe.call({method: "frappe_soca.api.test_login", args: {profile: frm.doc.name}});
      if (r.message && r.message.url) window.location.assign(r.message.url);
    });
    frappe.call({method: "frappe_soca.api.status", args: {profile: frm.doc.name}, callback: ({message}) => {
      if (!message) return;
      for (const field of message.deployment_locks) frm.set_df_property(field, "read_only", 1);
      frm.set_intro("Deployment values take precedence. State: " + (message.emergency_disabled ? "emergency disabled" : "candidate or checked") + ". Public metadata URL: " + frappe.utils.escape_html(message.client_id));
    }});
  }
});
