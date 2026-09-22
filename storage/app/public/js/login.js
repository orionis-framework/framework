/* Login: remembered username and password visibility. */
(() => {
  'use strict';

  // Server-provided old input takes precedence over the remembered username.
  const email = document.querySelector('[data-remembered-username]');
  if (email && !email.value) {
    const cookie = document.cookie.split(';').map((entry) => entry.trim())
      .find((entry) => entry.startsWith('usrname='));
    if (cookie) {
      try {
        email.value = decodeURIComponent(cookie.slice('usrname='.length));
      } catch {
        // A malformed cookie must not prevent password controls from working.
      }
    }
  }

  document.querySelectorAll('[data-password-toggle]').forEach((toggle) => {
    const input = document.getElementById(toggle.dataset.passwordToggle);
    if (!input) return;

    toggle.hidden = false;
    toggle.addEventListener('click', () => {
      const revealing = input.type === 'password';
      input.type = revealing ? 'text' : 'password';
      toggle.querySelector('[data-password-icon="show"]').hidden = revealing;
      toggle.querySelector('[data-password-icon="hide"]').hidden = !revealing;
      const label = revealing ? toggle.dataset.labelHide : toggle.dataset.labelShow;
      toggle.title = label;
      toggle.setAttribute('aria-label', label);
      toggle.setAttribute('aria-pressed', String(revealing));
    });
  });
})();
