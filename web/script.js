class Command {
    constructor() {
        this.element = document.querySelector(".command-display");
        this.value = "";
        this.inputs = {
            "Title": document.querySelector("input[placeholder='Title']"),
            "Category": document.querySelector("input[placeholder='Category']"),
            "Is Important": document.querySelector("input[name='Is Important']"),
            "Due": document.querySelector("input[placeholder='Due']"),
            "Description": document.querySelector("textarea[placeholder='Description']"),
            "Remind": document.querySelector("input[name='Remind']"),
            "Auto Done on Remind": document.querySelector("input[name='Auto Done on Remind']"),
        };
        this.updateValue();

        this.element.addEventListener("click", (event) => {
            let isValid = true;

            for (const key in this.inputs) {
                if (!this.inputs.hasOwnProperty(key)) continue;
                const element = this.inputs[key];

                if (element.hasAttribute("required") && !element.value) {
                    isValid = false;
                }
            }

            if (isValid) {
                navigator.clipboard.writeText(this.value);

                this.element.classList.add("success");
                this.element.textContent = "Copied!";

                setTimeout(() => {
                    this.updateValue();
                    this.element.classList.remove("success");
                    location.reload();
                }, 1000);
            } else {
                this.element.classList.add("error");
                this.element.textContent = "Missing required parameters!";

                setTimeout(() => {
                    this.updateValue();
                    this.element.classList.remove("error");
                }, 1000);
            }
        });

        for (const key in this.inputs) {
            if (!this.inputs.hasOwnProperty(key)) continue;

            const element = this.inputs[key];
            element.addEventListener("input", (event) => this.updateValue());

            if (element.hasAttribute("required")) {
                element.style.border = "0.5px solid var(--primary)";

                if (element.getAttribute("type") === "checkbox") {
                    element.nextElementSibling.style.color = "var(--primary)";
                }
            }
        }
    }

    updateValue() {
        const i = [];

        for (const key in this.inputs) {
            if (!this.inputs.hasOwnProperty(key)) continue;

            const element = this.inputs[key];
            let value;

            if (element.matches('[type="checkbox"]')) {
                value = element.checked ? "yes" : "no";
            } else {
                value = element.value;
            }

            if (hasWhiteSpace(value) || value.includes('"')) {
                value = `"${value.replaceAll('"', '\\"')}"`;
            }

            i.push(value || '""');
        }

        this.value = `watdo todo ${i.join(" ")}`;
        this.value = this.value.replaceAll("\n", "\\n");
        this.element.textContent = this.value;
    }
}

document.querySelector("textarea").addEventListener("keydown", (event) => {
    if (event.key == "Tab") {
        event.preventDefault();

        const element = event.target;
        var start = element.selectionStart;
        var end = element.selectionEnd;

        // set textarea value to: text before caret + tab + text after caret
        element.value = element.value.substring(0, start) +
            "    " + element.value.substring(end);

        // put caret at right position again
        element.selectionStart =
            element.selectionEnd = start + 4;

        element.dispatchEvent(new Event("input", { bubbles: true }));
    }
});

function hasWhiteSpace(string) {
    return /\s/g.test(string);
}

new Command();
