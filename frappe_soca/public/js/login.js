/* Use native login UI. No tokens or transaction secrets enter JavaScript storage. */
frappe.ready(() => {
  if (!window.location.pathname.endsWith("/login")) return;
  const container = document.querySelector(".page-card-actions") || document.querySelector(".login-content");
  if (!container) return;
  frappe.call({method: "frappe_soca.api.providers", callback: ({message}) => {
    for (const provider of message || []) {
      const link = document.createElement("a");
      link.className = "btn btn-default btn-sm btn-block";
      link.textContent = "Sign in with " + provider.label;
      link.href = provider.url;
      container.appendChild(link);
    }
  }});
});
