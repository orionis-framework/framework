/* Responsive navigation; native details keeps the user menu usable without JS. */
(() => {
  'use strict';

  const shell = document.querySelector('[data-dashboard-shell]');
  if (!shell) return;
  const sidebar = shell.querySelector('[data-sidebar]');
  const content = shell.querySelector('[data-shell-content]');
  const toggle = shell.querySelector('[data-sidebar-toggle]');
  const close = shell.querySelector('[data-sidebar-close]');
  const backdrop = shell.querySelector('[data-sidebar-backdrop]');
  const userMenu = shell.querySelector('[data-user-menu]');
  const desktop = window.matchMedia('(min-width: 992px)');
  const storageKey = 'orionis.sidebar.collapsed';
  let opened = false;
  let collapsed = false;

  try {
    collapsed = window.localStorage.getItem(storageKey) === 'true';
  } catch {
    // Navigation also works when browser storage is unavailable.
  }

  const updateToggle = () => {
    const expanded = desktop.matches ? !collapsed : opened;
    let label;
    if (desktop.matches) {
      label = collapsed ? toggle.dataset.labelExpand : toggle.dataset.labelCollapse;
    } else {
      label = opened ? toggle.dataset.labelClose : toggle.dataset.labelOpen;
    }
    toggle.setAttribute('aria-expanded', String(expanded));
    toggle.setAttribute('aria-label', label);
    toggle.title = label;
  };

  const setSidebar = (open, restoreFocus = true) => {
    opened = open && !desktop.matches;
    shell.classList.toggle('is-sidebar-open', opened);
    updateToggle();
    sidebar.inert = !desktop.matches && !opened;
    content.inert = opened;
    backdrop.hidden = !opened;
    document.body.classList.toggle('orionis-navigation-open', opened);
    if (opened) {
      sidebar.setAttribute('role', 'dialog');
      sidebar.setAttribute('aria-modal', 'true');
      close.focus();
    } else {
      sidebar.removeAttribute('role');
      sidebar.removeAttribute('aria-modal');
      if (restoreFocus && !desktop.matches) toggle.focus();
    }
  };

  const syncViewport = () => {
    const focused = document.activeElement;
    toggle.hidden = false;
    close.hidden = desktop.matches;
    shell.classList.toggle('is-sidebar-collapsed', desktop.matches && collapsed);
    setSidebar(false, false);
    if (!desktop.matches && sidebar.contains(focused)) toggle.focus();
    if (desktop.matches && focused === close) {
      sidebar.querySelector('a').focus();
    }
  };

  shell.classList.add('orionis-shell--enhanced');
  syncViewport();
  desktop.addEventListener('change', syncViewport);
  toggle.addEventListener('click', () => {
    if (!desktop.matches) {
      setSidebar(!opened);
      return;
    }
    collapsed = !collapsed;
    shell.classList.toggle('is-sidebar-collapsed', collapsed);
    updateToggle();
    try {
      window.localStorage.setItem(storageKey, String(collapsed));
    } catch {
      // The current page remains usable even if the preference cannot be saved.
    }
  });
  close.addEventListener('click', () => setSidebar(false));
  backdrop.addEventListener('click', () => setSidebar(false));
  sidebar.addEventListener('click', (event) => {
    if (opened && event.target.closest('a')) setSidebar(false);
  });

  document.addEventListener('click', (event) => {
    if (userMenu.open && !userMenu.contains(event.target)) userMenu.open = false;
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      if (opened) setSidebar(false);
      if (userMenu.open) {
        userMenu.open = false;
        userMenu.querySelector('summary').focus();
      }
    }
    if (event.key !== 'Tab' || !opened) return;
    const controls = [...sidebar.querySelectorAll('a[href], button:not([hidden])')];
    const first = controls[0];
    const last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
})();
