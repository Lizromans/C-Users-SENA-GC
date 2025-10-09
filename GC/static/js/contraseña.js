document.addEventListener("DOMContentLoaded", function () {
        const toggles = document.querySelectorAll(".edit-icon");

        toggles.forEach((toggle) => {
            toggle.addEventListener("click", function () {
            const input = this.previousElementSibling; // el input antes del ícono
            const icon = this.querySelector("i");

            if (input.type === "password") {
                input.type = "text";
                icon.classList.remove("fa-eye");
                icon.classList.add("fa-eye-slash");
            } else {
                input.type = "password";
                icon.classList.remove("fa-eye-slash");
                icon.classList.add("fa-eye");
            }
            });
        });
        });