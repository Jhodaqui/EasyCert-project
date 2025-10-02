// static/js/editor-docx.js
document.addEventListener("alpine:init", () => {

  // --- Store de gestión de DOCX (lista de certificados) ---
  Alpine.store("docxEditor", {
    open: false,
    userId: null,
    files: [],

    // Cargar archivos generados de un usuario
    async openForUser(userId) {
      this.userId = userId;
      this.open = true;
      this.files = [];

      try {
        const res = await fetch(`/documents/listar-docx-guardados/${userId}/`, {
          credentials: "include",
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
    },

    // Abrir vista previa de un archivo
    openPreview(filename) {
      Alpine.store("previewDocx").openForFile(this.userId, filename);
    },

    close() {
      this.open = false;
      this.userId = null;
      this.files = [];
    },
  });

  // --- Store de vista previa DOCX ---
  Alpine.store("previewDocx", {
    open: false,
    userId: null,
    fileName: null,

    async openForFile(userId, filename) {
      this.userId = userId;
      this.fileName = filename;
      this.open = true;

      const container = document.getElementById("docx-preview-container");
      container.innerHTML = "<p class='text-gray-500'>Cargando vista previa...</p>";

      try {
        const url = `/documents/contratos/preview/${userId}/${encodeURIComponent(filename)}/`;
        const res = await fetch(url);
        if (!res.ok) throw new Error("No se pudo cargar el archivo");

        const blob = await res.blob();
        container.innerHTML = "";

        // ⚡ Usar API oficial de docx-preview
        await window.docx.renderAsync(blob, container, null, {
          className: "docx-preview",
          inWrapper: true,
        });

      } catch (err) {
        console.error(err);
        container.innerHTML = `<div class="text-red-600">Error cargando vista previa</div>`;
      }
    },

    // Subir archivo editado
    async uploadEdited(event) {
      if (!this.userId) return;
      const file = event.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append("archivo", file);

      try {
        const res = await fetch(`/documents/contratos/upload/${this.userId}/`, {
          method: "POST",
          body: formData,
          credentials: "include",
          headers: { "X-CSRFToken": csrfToken },
        });
        const data = await res.json();
        if (data.ok) {
          Swal.fire("✅", "Archivo editado subido correctamente", "success");
          Alpine.store("docxEditor").openForUser(this.userId);
        } else {
          Swal.fire("❌", data.error || "Error al subir el archivo", "error");
        }
      } catch (err) {
        console.error(err);
        Swal.fire("❌ Error", "No se pudo subir el archivo", "error");
      }
    },

    close() {
      this.open = false;
      this.userId = null;
      this.fileName = null;
      document.getElementById("docx-preview-container").innerHTML = "";
    },
  });
});
