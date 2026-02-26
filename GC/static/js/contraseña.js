document.addEventListener("DOMContentLoaded", function () {
        const toggles = document.querySelectorAll(".edit-icon");

        toggles.forEach((toggle) => {
            toggle.addEventListener("click", function () {
            const input = this.previousElementSibling;
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

    document.getElementById('cambiarContraseñaModal').addEventListener('hidden.bs.modal', function () {
    // Limpiar campos
    document.getElementById('cambio-contraseña-form').reset();
    
    // Resetear todos los ojos a "cerrado"
    this.querySelectorAll('.edit-icon i').forEach(function(icono) {
        icono.classList.remove('fa-eye-slash');
        icono.classList.add('fa-eye');
    });

    // Volver todos los inputs a tipo password
    this.querySelectorAll('input[type="text"]').forEach(function(input) {
        input.type = 'password';
    });
});