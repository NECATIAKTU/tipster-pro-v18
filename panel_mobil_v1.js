(() => {
    "use strict";

    const list = document.getElementById("tp-list");

    if (!list) return;

    function element(tag, text, className) {
        const node = document.createElement(tag);

        if (text !== undefined) {
            node.textContent = text;
        }

        if (className) {
            node.className = className;
        }

        return node;
    }

    function createDetail(name, pick, meta, probs) {
        const detail = element(
            "section", undefined, "pm-detail"
        );

        const back = element(
            "button",
            "← Maç listesine dön",
            "pm-back"
        );

        back.type = "button";

        back.addEventListener("click", () => {
            detail.remove();

            for (const child of list.children) {
                if (child.dataset.pmHidden === "1") {
                    child.hidden = false;
                    delete child.dataset.pmHidden;
                }
            }
        });

        detail.append(back);

        detail.append(
            element("h2", name, "pm-detail-title")
        );

        detail.append(
            element("p", meta, "tp-note")
        );

        detail.append(
            element("div", pick, "pm-detail-pick")
        );

        detail.append(
            element("h3", "Gol analizleri")
        );

        for (const item of probs) {
            const row = element(
                "div", undefined, "pm-prob-row"
            );

            const label = element(
                "span", item.label
            );

            const track = element(
                "div", undefined, "pm-prob-track"
            );

            const fill = element(
                "div", undefined, "pm-prob-fill"
            );

            const value = Number(
                item.value
                    .replace("%", "")
                    .replace(",", ".")
                    .trim()
            );

            if (
                Number.isFinite(value) &&
                value >= 0 &&
                value <= 100
            ) {
                fill.style.width = value + "%";
            } else {
                fill.style.width = "0%";
            }

            track.append(fill);

            row.append(
                label,
                track,
                element(
                    "span",
                    item.value,
                    "pm-prob-value"
                )
            );

            detail.append(row);
        }

        return detail;
    }

    function convert(card) {
        if (card.dataset.pmReady === "1") return;

        const title = card.querySelector("h3");
        const prediction = card.querySelector(".tp-pick");
        const info = card.querySelector("small");

        if (!title || !prediction) return;

        const name = title.textContent.trim();
        const pick = prediction.textContent.trim();

        const meta = info
            ? info.textContent.trim()
            : "";

        const probs = Array.from(
            card.querySelectorAll(".tp-probs span")
        ).map(item => {
            const value = item.querySelector("b");
            const copy = item.cloneNode(true);

            copy.querySelector("b")?.remove();

            return {
                label: copy.textContent.trim(),
                value: value
                    ? value.textContent.trim()
                    : "—"
            };
        });

        const extra = Array.from(
            card.querySelectorAll("small")
        ).slice(1).map(
            node => node.textContent.trim()
        );

        const button = element(
            "button",
            undefined,
            "pm-match-button"
        );

        button.type = "button";

        const pickNode = element(
            "span", pick, "pm-match-pick"
        );

        if (!/^[1-6]\.5 ÜST/.test(pick)) {
            pickNode.classList.add("pm-risk");
        }

        button.append(
            element("span", name, "pm-match-name"),
            pickNode,
            element("span", "›", "pm-match-arrow")
        );

        button.addEventListener("click", () => {
            list.querySelector(".pm-detail")?.remove();

            for (const child of list.children) {
                if (!child.hidden) {
                    child.dataset.pmHidden = "1";
                    child.hidden = true;
                }
            }

            const detail = createDetail(
                name, pick, meta, probs
            );

            for (const text of extra) {
                detail.append(
                    element("p", text, "tp-note")
                );
            }

            list.prepend(detail);

            detail.scrollIntoView({
                block: "start"
            });

            detail.querySelector("button").focus({
                preventScroll: true
            });
        });

        card.dataset.pmReady = "1";
        card.className = "pm-match";
        card.replaceChildren(button);
    }

    function refresh() {
        list.querySelectorAll(
            ".tp-match"
        ).forEach(convert);

        const daily = document.querySelector(
            '[data-tp="today"] b'
        );

        if (
            daily &&
            daily.textContent !== "GÜNLÜK TAHMİNLER"
        ) {
            daily.textContent = "GÜNLÜK TAHMİNLER";
        }
    }

    const observer = new MutationObserver(refresh);

    observer.observe(list, {
        childList: true
    });

    refresh();

})();
/* ULKE VE LIG MERKEZI - MOBIL V1 */

(() => {
    "use strict";

    const body = document.getElementById("lc-current");

    if (!body) return;

    const lines = ["1.5", "2.5", "3.5", "4.5", "5.5", "6.5"];

    function el(tag, text, cls) {
        const node = document.createElement(tag);
        if (text !== undefined) node.textContent = text;
        if (cls) node.className = cls;
        return node;
    }

    function convert() {
        for (const row of body.rows) {
            if (row.dataset.pmReady) continue;
            if (row.cells.length !== 10) continue;

            const values = Array.from(
                row.cells,
                cell => cell.textContent.trim()
            );

            row.dataset.pmReady = "1";

            const cell = el("td");
            cell.colSpan = 10;
            cell.style.gridColumn = "1 / -1";

            const button = el(
                "button", undefined, "pm-match-button"
            );

            button.type = "button";

            const pick = el(
                "span", values[3], "pm-match-pick"
            );

            if (!/^[1-6]\.5 ÜST/.test(values[3])) {
                pick.classList.add("pm-risk");
            }

            button.append(
                el("span", values[0], "pm-match-name"),
                pick,
                el("span", "›", "pm-match-arrow")
            );

            const detail = el(
                "section", undefined, "pm-detail"
            );

            detail.hidden = true;

            detail.append(
                el("h2", values[0], "pm-detail-title"),
                el("p", values[1], "tp-note"),
                el("p", values[2], "tp-note")
            );

            for (let i = 0; i < lines.length; i++) {
                const item = el(
                    "div", undefined, "pm-prob-row"
                );

                const track = el(
                    "div", undefined, "pm-prob-track"
                );

                const fill = el(
                    "div", undefined, "pm-prob-fill"
                );

                const value = parseFloat(
                    values[i + 4]
                        .replace("%", "")
                        .replace(",", ".")
                );

                fill.style.width =
                    Number.isFinite(value) &&
                    value >= 0 && value <= 100
                        ? value + "%"
                        : "0%";

                track.append(fill);

                item.append(
                    el("span", lines[i] + " ÜST"),
                    track,
                    el(
                        "span",
                        values[i + 4],
                        "pm-prob-value"
                    )
                );

                detail.append(item);
            }

            button.setAttribute(
                "aria-expanded", "false"
            );

            button.addEventListener("click", () => {
                detail.hidden = !detail.hidden;

                button.setAttribute(
                    "aria-expanded",
                    String(!detail.hidden)
                );
            });

            cell.append(button, detail);
            row.replaceChildren(cell);
        }
    }

    const mode = document.getElementById("lc-mode");

    if (
        mode &&
        !Array.from(mode.options).some(
            option => option.value === "20"
        )
    ) {
        mode.append(new Option("TOP 20", "20"));
    }

    new MutationObserver(convert).observe(body, {
        childList: true
    });

    convert();

})();
