document.addEventListener("alpine:init", () => {
  Alpine.store("docxEditor", {
    open: false,
    userId: null,
    files: [],

    async openForUser(userId) {
      this.userId = userId;
      this.open = true;
      this.files = [];
      try {
        const res = await fetch(`/documents/listar-docx-guardados/${userId}/`, {
          credentials: "include"   // 👈 manda cookies de sesión
        });
        const data = await res.json();
        if (data.ok) {
          this.files = data.files || [];
        } else {
          Swal.fire("⚠️", data.error || "No se encontraron archivos", "warning");
        }
      } catch (err) {
        console.error(err);
        Swal.fire("❌ Error", "No se pudieron cargar los archivos", "error");
      }
    }, // openForUser

    async loadPreview(filename) {
      if (!this.userId) return;
      const container = document.getElementById("docxEditorContainer");
      container.innerHTML = `<p class="text-gray-500">Cargando vista previa...</p>`;
      try {
        const res = await fetch(`/documents/preview-docx/${this.userId}/${encodeURIComponent(filename)}/`, {
          credentials: "include"   // 👈 cookies incluidas
        });
        const data = await res.json();
        if (data.ok) {
          container.innerHTML = data.html;
        } else {
          container.innerHTML = `<div class="text-red-600">${data.error}</div>`;
        }
      } catch (err) {
        console.error(err);
        container.innerHTML = `<div class="text-red-600">Error cargando vista previa</div>`;
      }
    }, // loadPreview

    close() {
      this.open = false;
      this.userId = null;
      this.files = [];
      document.getElementById("docxEditorContainer").innerHTML = ""; 
    } // close

  }); // Alpine.store
}); // alpine:init

// Función global para guardar la fecha de expedición
window.__saveFechaPreview = async function(filename) {
  const input = document.getElementById("fecha_expedicion_input");
  if (!input) { Swal.fire("❌", "No se encontró el input", "error"); return; }
  const fecha = input.value;
  if (!fecha) { Swal.fire("⚠️", "Debes escribir una fecha", "warning"); return; }

  const store = Alpine.store("docxEditor");
  try {
    const res = await fetch(`/documents/update-fecha-expedicion/${store.userId}/${encodeURIComponent(filename)}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
      body: JSON.stringify({ fecha_expedicion: fecha }),
      credentials: "include"   // 👈 cookies incluidas
    });
    const data = await res.json();
    if (data.ok) {
      Swal.fire("✅", data.message, "success");
      await store.loadPreview(filename);
    } else {
      Swal.fire("❌", data.error || "Error guardando fecha", "error");
    }
  } catch (err) {
    console.error(err);
    Swal.fire("❌ Error", "No se pudo guardar la fecha", "error");
  }
};
