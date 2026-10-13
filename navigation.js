"use strict";
(() => {
  const sections = [document.getElementById("lernangebot"), document.getElementById("studienprojekt")];
  const links = [...document.querySelectorAll(".navigation a")];
  const showSection = (id) => {
    if (!sections.some(section => section.id === id)) return;
    sections.forEach(section => { section.hidden = section.id !== id; });
    links.forEach(link => {
      if (link.hash === "#" + id) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  };
  document.documentElement.classList.add("js-navigation");
  showSection(location.hash === "#studienprojekt" ? "studienprojekt" : "lernangebot");
  links.forEach(link => link.addEventListener("click", event => {
    event.preventDefault();
    showSection(link.hash.slice(1));
    history.pushState(null, "", link.hash);
    const heading = document.querySelector(link.hash + " h1, " + link.hash + " h2");
    if (heading) { heading.setAttribute("tabindex", "-1"); heading.focus(); }
  }));
  const syncLocation = () => {
    showSection(location.hash === "#studienprojekt" ? "studienprojekt" : "lernangebot");
    if (location.hash === "#einheit-1-2") {
      const unit = document.getElementById("einheit-1-2");
      if (unit) { unit.open = true; unit.scrollIntoView({block:"start"}); }
    }
  };
  syncLocation();
  window.addEventListener("popstate", syncLocation);
  window.addEventListener("hashchange", syncLocation);
})();
