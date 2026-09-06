document.addEventListener("DOMContentLoaded", () => {

    const form = document.querySelector(".farm-form");

    if (!form) {
        return;
    }


    form.addEventListener("submit", () => {

        const button = form.querySelector(".primary-button");

        if (!button) {
            return;
        }

        button.disabled = true;

        button.innerHTML = `
            Analysing farm data...
            <span>⏳</span>
        `;

    });

});