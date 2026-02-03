document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("modal-eliminar-recurso");
  const texto = document.getElementById("texto-modal-recurso");
  const form = document.getElementById("form-eliminar-recurso");
  const cancelar = document.getElementById("cancelar-recurso");

  if (!modal || !texto || !form || !cancelar) {
    console.warn("⚠️ Modal de eliminar recurso no encontrado.");
    return;
  }

  document.addEventListener("click", function (e) {
    const boton = e.target.closest(".eliminar-recurso");
    if (!boton) return;

    e.preventDefault();
    e.stopPropagation();

    const nombre = boton.dataset.nombre || "este recurso";
    const url = boton.dataset.url;

    texto.innerHTML = `¿Deseas eliminar el recurso <b>${nombre}</b>?`;
    form.action = url;
    modal.classList.add("activo");
  });

  cancelar.addEventListener("click", function () {
    modal.classList.remove("activo");
  });

  modal.addEventListener("click", function (e) {
    if (e.target === modal) {
      modal.classList.remove("activo");
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && modal.classList.contains("activo")) {
      modal.classList.remove("activo");
    }
  });
});
