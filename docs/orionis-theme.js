/* Runs before stylesheets to apply the saved theme without a color flash. */
(function () {
  "use strict";
  document.documentElement.lang = "en";
  var preference;
  try {
    preference = window.localStorage.getItem("orionis-api-theme");
  } catch (error) {
    // The system preference also works when browser storage is unavailable.
  }
  var isDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  var theme = preference === "light" || preference === "dark" ? preference : (isDark ? "dark" : "light");
  document.documentElement.dataset.theme = theme;
  document.documentElement.dataset.apiIndex = /(?:\/|\/(?:index|orionis)\.html)$/.test(window.location.pathname) ? "true" : "false";
  document.documentElement.style.colorScheme = theme;
})();
