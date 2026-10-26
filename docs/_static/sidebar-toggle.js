// Fallback for Sphinx Book Theme sidebar buttons that lack an active click handler.
// Only intervene when the theme's own handler did not change the checkbox.
(() => {
  "use strict";

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;

    const button = target.closest(".sidebar-toggle");
    if (!button || !button.matches(".pst-navbar-icon, .header-article-item .sidebar-toggle")) return;

    const primary = button.classList.contains("primary-toggle");
    const secondary = button.classList.contains("secondary-toggle");
    if (!primary && !secondary) return;

    const checkbox = document.getElementById(
      primary ? "pst-primary-sidebar-checkbox" : "pst-secondary-sidebar-checkbox"
    );
    if (!checkbox) return;

    const wasChecked = checkbox.checked;
    // Give built-in handlers (and label default actions) a chance to work first.
    window.setTimeout(() => {
      if (checkbox.checked !== wasChecked) return;
      checkbox.checked = !wasChecked;
      checkbox.dispatchEvent(new Event("change", { bubbles: true }));
    }, 0);
  }, true);
})();
