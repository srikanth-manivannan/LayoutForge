/* Mockup-only helpers: theme toggle (persisted) + mockup navigation.
   Not product code — the product wires themes through Settings. */
(function () {
  var saved = localStorage.getItem("lf-mock-theme");
  if (saved === "dark") document.documentElement.setAttribute("data-lf-theme", "dark");

  window.lfToggleTheme = function () {
    var root = document.documentElement;
    var dark = root.getAttribute("data-lf-theme") === "dark";
    if (dark) root.removeAttribute("data-lf-theme");
    else root.setAttribute("data-lf-theme", "dark");
    localStorage.setItem("lf-mock-theme", dark ? "light" : "dark");
  };
})();
