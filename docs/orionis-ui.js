/* Progressive enhancements only: navigation, search, and API rendering stay native to Pydoctor. */
(function () {
  "use strict";

  var root = document.documentElement;
  var themeButton = document.getElementById("orionis-theme-toggle");
  var menuButton = document.getElementById("orionis-menu-toggle");
  var sidebar = document.querySelector(".sidebarcontainer");
  var search = document.getElementById("search-box");
  var mobile = window.matchMedia("(max-width: 760px)");
  var systemTheme = window.matchMedia("(prefers-color-scheme: dark)");
  var explicitTheme = false;

  var content = document.querySelector("main") || document.querySelector("body > .container-fluid");
  if (content) {
    content.id = "orionis-content";
    content.tabIndex = -1;
    var skip = document.createElement("a");
    skip.className = "orionis-skip-link";
    skip.href = "#orionis-content";
    skip.textContent = "Skip to content";
    document.body.insertBefore(skip, document.body.firstChild);
  }

  try {
    explicitTheme = /^(light|dark)$/.test(window.localStorage.getItem("orionis-api-theme"));
  } catch (error) {
    // Session-only theme switching remains available.
  }

  function updateThemeButton() {
    if (!themeButton) return;
    var dark = root.dataset.theme === "dark";
    var label = "Switch to " + (dark ? "light" : "dark") + " theme";
    themeButton.setAttribute("aria-label", label);
    themeButton.setAttribute("title", label);
    themeButton.hidden = false;
  }

  function applyTheme(theme) {
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    updateThemeButton();
  }

  if (themeButton) {
    themeButton.addEventListener("click", function () {
      var theme = root.dataset.theme === "dark" ? "light" : "dark";
      explicitTheme = true;
      applyTheme(theme);
      try {
        window.localStorage.setItem("orionis-api-theme", theme);
      } catch (error) {
        // Private browsing and local files may deny storage.
      }
    });
    updateThemeButton();
  }

  function followSystemTheme(event) {
    if (!explicitTheme) applyTheme(event.matches ? "dark" : "light");
  }
  if (systemTheme.addEventListener) systemTheme.addEventListener("change", followSystemTheme);

  function setMenu(open, restoreFocus) {
    document.body.classList.toggle("orionis-menu-open", open);
    if (menuButton) {
      menuButton.setAttribute("aria-expanded", String(open));
      menuButton.setAttribute("aria-label", (open ? "Close" : "Open") + " API navigation");
      if (restoreFocus) menuButton.focus();
    }
  }

  if (sidebar && menuButton) {
    sidebar.id = "orionis-sidebar";
    menuButton.setAttribute("aria-controls", sidebar.id);
    menuButton.hidden = false;
    menuButton.addEventListener("click", function () {
      setMenu(!document.body.classList.contains("orionis-menu-open"));
    });
    sidebar.addEventListener("click", function (event) {
      if (mobile.matches && event.target.closest("a[href]")) setMenu(false);
    });
    document.addEventListener("click", function (event) {
      if (document.body.classList.contains("orionis-menu-open") && !sidebar.contains(event.target) && !menuButton.contains(event.target)) {
        setMenu(false);
      }
    });
    if (mobile.addEventListener) mobile.addEventListener("change", function () { setMenu(false); });
  }

  // Pydoctor's sidebar controls are labels and a link without href. Add keyboard support.
  document.querySelectorAll(".sidebar label[for]").forEach(function (label) {
    var input = document.getElementById(label.htmlFor);
    if (!input || !input.classList.contains("tocChildrenToggle")) return;
    var item = label.parentElement.querySelector("a");
    var name = item ? item.textContent.trim() : "API section";
    label.tabIndex = 0;
    label.setAttribute("role", "button");
    function syncLabel() {
      label.setAttribute("aria-expanded", String(input.checked));
      label.setAttribute("aria-label", (input.checked ? "Collapse " : "Expand ") + name);
    }
    input.addEventListener("change", syncLabel);
    label.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        input.click();
      }
    });
    syncLabel();
  });

  var collapse = document.querySelector("#collapse-sidebar a");
  if (collapse) {
    collapse.tabIndex = 0;
    collapse.setAttribute("role", "button");
    collapse.setAttribute("aria-controls", "orionis-sidebar");
    function syncCollapse() {
      var collapsed = document.body.classList.contains("sidebar-collapsed");
      collapse.setAttribute("aria-expanded", String(!collapsed));
      collapse.setAttribute("aria-label", (collapsed ? "Expand" : "Collapse") + " API navigation");
    }
    collapse.addEventListener("click", syncCollapse);
    collapse.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        collapse.click();
      }
    });
    syncCollapse();
  }

  var currentPage = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".mainnavbar .navlinks > a").forEach(function (link) {
    if (link.getAttribute("href") === currentPage) link.setAttribute("aria-current", "page");
  });

  if (search) {
    search.setAttribute("placeholder", "Search the API…");
    search.setAttribute("aria-label", "Search the Orionis API");
    search.setAttribute("aria-keyshortcuts", "/ Control+k Meta+k");
    search.setAttribute("title", "Search the API (/ or Ctrl+K)");
    var hint = document.createElement("kbd");
    hint.className = "orionis-search-hint";
    hint.setAttribute("aria-hidden", "true");
    hint.textContent = "/";
    search.parentElement.insertBefore(hint, search.nextSibling);
  }
  var clearButton = document.getElementById("search-clear-button");
  if (clearButton) {
    clearButton.tabIndex = 0;
    clearButton.setAttribute("role", "button");
    clearButton.setAttribute("aria-label", "Clear API search");
    clearButton.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        clearButton.click();
        if (search) search.focus();
      }
    });
  }
  var searchStatus = document.getElementById("search-status");
  if (searchStatus) searchStatus.setAttribute("role", "status");

  document.addEventListener("keydown", function (event) {
    if (event.isComposing) return;
    var target = event.target;
    var editing = target instanceof Element && (target.matches("input, textarea, select") || target.isContentEditable);
    var searchShortcut = (event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey) ||
      (event.key.toLowerCase() === "k" && (event.ctrlKey || event.metaKey) && !event.altKey);
    if (search && searchShortcut && !editing) {
      event.preventDefault();
      setMenu(false);
      search.focus();
      search.select();
    }
    if (event.key === "Escape") {
      if (document.body.classList.contains("orionis-menu-open")) setMenu(false, true);
      if (search && (target === search || document.getElementById("search-results-container").style.display !== "none")) {
        if (typeof window.clearSearch === "function") window.clearSearch();
      }
    }
  });

  function fallbackCopy(text) {
    var field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("aria-label", "Code to copy");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.select();
    var copied = false;
    try { copied = document.execCommand("copy"); } catch (error) { /* Report failure below. */ }
    field.remove();
    return copied;
  }

  document.querySelectorAll("pre.py-doctest, pre.rst-literal-block").forEach(function (pre) {
    var code = pre.textContent;
    var wrapper = document.createElement("div");
    wrapper.className = "orionis-code-block";
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);
    var button = document.createElement("button");
    button.className = "orionis-copy-button";
    button.type = "button";
    button.textContent = "Copy";
    button.setAttribute("aria-label", "Copy code example");
    button.setAttribute("aria-live", "polite");
    wrapper.appendChild(button);
    button.addEventListener("click", async function () {
      var copied = false;
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(code);
          copied = true;
        }
      } catch (error) { /* Try the browser's legacy clipboard API next. */ }
      if (!copied) copied = fallbackCopy(code);
      button.focus();
      button.textContent = copied ? "Copied" : "Select to copy";
      button.setAttribute("aria-label", copied ? "Code copied" : "Copy unavailable. Select the code and copy manually.");
      if (!copied) {
        var range = document.createRange();
        range.selectNodeContents(pre);
        var selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      }
      window.setTimeout(function () {
        button.textContent = "Copy";
        button.setAttribute("aria-label", "Copy code example");
      }, 2200);
    });
  });
})();
