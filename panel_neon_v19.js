/* TIPSTER PRO - NEON MENU V19 */

(() => {
  "use strict";

  function init() {
    const header = document.querySelector("body > header");
    const home = document.getElementById("tp-home");

    if (!header || !home) return;
    if (document.getElementById("neon-menu")) return;

    const toggle = document.createElement("button");
    toggle.id = "neon-toggle";
    toggle.type = "button";
    toggle.textContent = "☰";
    toggle.setAttribute("aria-label", "Ana menüyü aç");
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-controls", "neon-menu");

    header.prepend(toggle);

    const overlay = document.createElement("div");
    overlay.id = "neon-overlay";
    overlay.hidden = true;

    const menu = document.createElement("aside");
    menu.id = "neon-menu";
    menu.hidden = true;
    menu.setAttribute("aria-label", "TIPSTER PRO menüsü");

    const title = document.createElement("h2");
    title.textContent = "TIPSTER PRO V18";

    const close = document.createElement("button");
    close.type = "button";
    close.textContent = "✕ Menüyü kapat";

    const content = document.createElement("div");
    content.id = "neon-menu-content";

    menu.append(title, close, content);
    document.body.append(overlay, menu);

    function hide() {
      menu.hidden = true;
      overlay.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      toggle.focus();
    }

    function addButton(text, action) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "neon-menu-item";
      button.textContent = text;

      button.addEventListener("click", () => {
        hide();
        action();
      });

      content.append(button);
    }

    function show() {
      content.replaceChildren();

      addButton("⌂ Ana ekran", () => {
        const back = document.getElementById("tp-home-button");
        if (back && !home.hidden) {
          window.scrollTo(0, 0);
        } else if (back) {
          back.click();
        }
      });

      for (const group of home.querySelectorAll(".tp-group")) {
        const heading = group.querySelector("h2");
        const grid = group.querySelector(".tp-grid");

        if (!grid) continue;

        if (heading) {
          const label = document.createElement("h3");
          label.textContent = heading.textContent;
          content.append(label);
        }

        for (const original of grid.children) {
          if (original.tagName !== "BUTTON") continue;

          const name = original.querySelector("b");
          const text = (name || original).textContent.trim();

          addButton(text, () => {
            if (original.dataset.tp) {
              if (typeof window.tpOpen === "function") {
                window.tpOpen(original.dataset.tp);
              } else {
                original.click();
              }
            } else {
              if (home.hidden) {
                window.tpOpen?.("home");
              }
              original.click();
              original.scrollIntoView({
                block: "start"
              });
            }
          });
        }
      }

      overlay.hidden = false;
      menu.hidden = false;
      toggle.setAttribute("aria-expanded", "true");
      close.focus();
    }

    toggle.addEventListener("click", () => {
      if (menu.hidden) show();
      else hide();
    });

    close.addEventListener("click", hide);
    overlay.addEventListener("click", hide);

    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && !menu.hidden) {
        hide();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
/* V19 - YESIL BASARI CEMBERI */

(() => {
  "use strict";

  function initRing() {
    const intro = document.getElementById("dashboard-intro");
    const source = document.getElementById("winrate");

    if (!intro || !source) return;
    if (document.getElementById("neon-success-ring")) return;

    const card = document.createElement("div");
    card.id = "neon-success-card";

    const ring = document.createElement("div");
    ring.id = "neon-success-ring";

    const value = document.createElement("strong");
    value.id = "neon-success-value";
    value.textContent = "—";

    const label = document.createElement("small");
    label.textContent = "GERCEK BASARI";

    ring.append(value);
    card.append(ring, label);
    intro.append(card);

    function update() {
      const raw = source.textContent.trim();
      const match = raw.match(/\d+(?:[.,]\d+)?/);

      const rate = match
        ? Number(match[0].replace(",", "."))
        : NaN;

      if (!Number.isFinite(rate) ||
          rate < 0 || rate > 100) {
        value.textContent = "—";
        ring.style.setProperty("--rate", "0%");
        return;
      }

      value.textContent = "%" + rate.toFixed(1);
      ring.style.setProperty(
        "--rate", rate + "%"
      );
    }

    const observer = new MutationObserver(update);

    observer.observe(source, {
      childList: true,
      characterData: true,
      subtree: true
    });

    update();
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded", initRing
    );
  } else {
    initRing();
  }
})();

/* V19 - BASARI CEMBERI END */
