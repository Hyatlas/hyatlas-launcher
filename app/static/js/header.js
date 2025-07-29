/*****************************************************************
 *  Globale Header-Navigation   (wird auf jeder Seite geladen)
 *****************************************************************/
(function () {
  // Mapping Button-ID ➜ Ziel-URL
  const navMap = {
    home    : "/",
    servers : "/servers",
    avatar  : "/avatar",
    settings: "/settings",
    adventure : "/adventure",
    quit    : "quit"
  };

  const buttons = document.querySelectorAll(".nav-btn");

  /* Klick-Handler */
  function handleClick (e) {
    const act = e.currentTarget.dataset.act;
    if (act === "quit") {
      // Desktop-Build bekommt ein pywebview-Quit,
      // im Browser schließen wir einfach das Fenster
      if (window.pywebview?.api?.quit) { window.pywebview.api.quit(); }
      else { window.close(); }
      return;
    }
    const target = navMap[act] || "/";
    window.location.href = target;
  }

  /* Listener setzen & aktive Seite markieren */
  const currentPath = window.location.pathname;
  buttons.forEach(btn => {
    btn.addEventListener("click", handleClick);

    // aktive Seite farblich hervorheben
    const act   = btn.dataset.act;
    const route = navMap[act];
    if (route && currentPath.startsWith(route)) {
      btn.classList.add("active");
    }
  });
})();
