(() => {
  "use strict";

  const results = window.PORTFOLIO_RESULTS || {};
  const menuButton = document.querySelector("#menu-button");
  const scrim = document.querySelector("#mobile-scrim");
  const navLinks = Array.from(document.querySelectorAll(".nav-link"));
  const progressBar = document.querySelector("#reading-progress-bar");

  function readPath(object, path) {
    return path.split(".").reduce((value, key) => {
      if (value === undefined || value === null) return undefined;
      return value[key];
    }, object);
  }

  function format(value, mode) {
    if (mode === "text") return value ?? "—";
    if (value === undefined || value === null || Number.isNaN(Number(value))) return "—";
    if (mode === "percent") return `${(Number(value) * 100).toFixed(2)}%`;
    if (mode === "bps") return `${(Number(value) * 10_000).toFixed(1)} bps`;
    if (mode === "decimal") return Number(value).toFixed(3);
    return String(value);
  }

  document.querySelectorAll("[data-result]").forEach((element) => {
    const value = readPath(results, element.dataset.result);
    element.textContent = format(value, element.dataset.format);
  });

  document.querySelectorAll("[data-weight]").forEach((element) => {
    const value = results.latest_weights?.[element.dataset.weight];
    element.textContent = format(value, "percent");
  });

  document.querySelectorAll("[data-risk]").forEach((element) => {
    const value = results.risk_contribution?.[element.dataset.risk];
    element.textContent = format(value, "percent");
  });

  document.querySelectorAll("[data-contribution]").forEach((element) => {
    const value = results.annual_return_contribution?.[element.dataset.contribution];
    element.textContent = format(value, "percent");
  });

  function closeMenu({ restoreFocus = false } = {}) {
    document.body.classList.remove("nav-open");
    menuButton.setAttribute("aria-expanded", "false");
    menuButton.setAttribute("aria-label", "Open case navigation");
    scrim.hidden = true;
    if (restoreFocus) menuButton.focus();
  }

  function openMenu() {
    document.body.classList.add("nav-open");
    menuButton.setAttribute("aria-expanded", "true");
    menuButton.setAttribute("aria-label", "Close case navigation");
    scrim.hidden = false;
  }

  menuButton?.addEventListener("click", () => {
    if (document.body.classList.contains("nav-open")) closeMenu({ restoreFocus: true });
    else openMenu();
  });

  scrim?.addEventListener("click", () => closeMenu({ restoreFocus: true }));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && document.body.classList.contains("nav-open")) {
      closeMenu({ restoreFocus: true });
    }
  });
  navLinks.forEach((link) => link.addEventListener("click", () => {
    if (window.matchMedia("(max-width: 1000px)").matches) closeMenu();
  }));

  function updateProgress() {
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    const value = scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0;
    progressBar.style.width = `${Math.min(100, Math.max(0, value))}%`;
  }

  let ticking = false;
  window.addEventListener("scroll", () => {
    if (ticking) return;
    requestAnimationFrame(() => {
      updateProgress();
      ticking = false;
    });
    ticking = true;
  }, { passive: true });

  if ("IntersectionObserver" in window) {
    const sections = Array.from(document.querySelectorAll("main section[id]"));
    const sectionObserver = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
      if (!visible.length) return;
      const activeId = visible[0].target.id;
      navLinks.forEach((link) => {
        const isActive = link.getAttribute("href") === `#${activeId}`;
        link.classList.toggle("is-active", isActive);
        if (isActive) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    }, { rootMargin: "-16% 0px -68% 0px", threshold: [0.01, 0.2] });
    sections.forEach((section) => sectionObserver.observe(section));

    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            revealObserver.unobserve(entry.target);
          }
        });
      }, { threshold: 0.08 });
      document.querySelectorAll(".figure-panel, .metric-grid, .risk-grid").forEach((element) => {
        element.classList.add("reveal");
        revealObserver.observe(element);
      });
    }
  }

  updateProgress();
})();
