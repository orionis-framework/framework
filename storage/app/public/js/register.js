/* Registration: independent visibility controls for both password fields. */
(() => {
  'use strict';

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
