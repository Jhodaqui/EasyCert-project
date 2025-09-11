// static/js/dashboard.js
$(document).ready(function () {
  // ==============================
  // Referencias de modales y elementos
  // ==============================
  const listModalEl = document.getElementById('contratoModal');          // Modal LISTA
  const listModalBody = document.getElementById('contratosModalBody');

  const formModalEl = document.getElementById('contratoFormModal');      // Modal FORM
  const formModal = () => new bootstrap.Modal(formModalEl);
  const form = document.getElementById('contratoFormModalForm');

  // Elementos del FORM
  const formAlerts = document.getElementById('formModalAlerts');
  const formErrors = document.getElementById('formModalErrors');
  const guardarOtroBtn = document.getElementById('guardarOtroBtn');
  const guardarBtnForm = document.getElementById('guardarBtnForm');

  const numeroContratoInput = document.getElementById("id_numero_contrato");
  const archivoInput = document.getElementById("id_archivo");
  const archivoInputWrapper = archivoInput.closest(".col-12");

  const wrapperObjeto = document.getElementById("wrapper_objeto");
  const wrapperObjetivos = document.getElementById("wrapper_objetivos");

  // ==============================
  // Helpers UI
  // ==============================
  function resetFormModalUI() {
    form.reset();
    if (formAlerts) formAlerts.style.display = 'none';
    if (formErrors) formErrors.innerHTML = '';

    if (wrapperObjeto) wrapperObjeto.style.display = "none";
    if (wrapperObjetivos) wrapperObjetivos.style.display = "none";
    if (archivoInputWrapper) archivoInputWrapper.style.display = "none";

    if (guardarBtnForm) {
      guardarBtnForm.style.display = "inline-block";
      guardarBtnForm.textContent = "Guardar";
    }
    if (guardarOtroBtn) guardarOtroBtn.style.display = "none";

    const hiddenId = document.getElementById("modal_contrato_id");
    if (hiddenId) hiddenId.remove();
  }

  function showFormErrors(errs) {
    formErrors.innerHTML = '';
    for (const k in errs) {
      const msgs = errs[k];
      if (Array.isArray(msgs)) {
        msgs.forEach(m => formErrors.innerHTML += `<div>${k}: ${m}</div>`);
      } else {
        formErrors.innerHTML += `<div>${k}: ${msgs}</div>`;
      }
    }
    formAlerts.style.display = 'block';
  }

  // ==============================
  // 1) Refrescar LISTA de contratos en el modal de lista
  // ==============================
  async function refrescarContratosCargados(userId) {
    try {
      listModalBody.innerHTML = `<p class="text-muted">Cargando contratos...</p>`;
      const res = await fetch(urls.verContratosBase + userId + "/");
      const data = await res.json();

      listModalBody.innerHTML = `
        <div id="contratosCargadosWrapper" class="mt-2">
          <div class="table-responsive">${data.html}</div>
        </div>
      `;

      bindAccionesContratos(userId);
    } catch (err) {
      console.error("Error refrescando contratos:", err);
      listModalBody.innerHTML = `<div class="alert alert-danger">Error cargando contratos.</div>`;
    }
  }

  // ==============================
  // 2) Acciones en la tabla de la LISTA
  // ==============================
  function bindAccionesContratos(userId) {
    // Select/Deselect all
    const selectAll = document.getElementById("selectAllContratos");
    if (selectAll) {
      selectAll.addEventListener("change", function () {
        document.querySelectorAll("#contratosCargadosWrapper .contrato-checkbox")
          .forEach(cb => cb.checked = selectAll.checked);
      });
    }

    // 📄 Botón PDF → abre certificado del contrato seleccionado
    document.querySelectorAll(".generar-pdf").forEach(btn => {
      btn.addEventListener("click", function () {
        const contratoId = this.dataset.id;
        const url = `/documents/contrato/pdf/${userId}/${contratoId}/`;
        window.open(url, "_blank"); // abre en nueva pestaña
      });
    });

    // Generar Individual (ZIP)
    const btnIndividual = document.getElementById("generarIndividual");
    if (btnIndividual) {
      btnIndividual.onclick = async function () {
        const seleccionados = Array.from(document.querySelectorAll("#contratosCargadosWrapper .contrato-checkbox:checked"))
          .map(cb => cb.value);

        if (seleccionados.length === 0) {
          alert("⚠️ Selecciona al menos un contrato.");
          return;
        }

        try {
          const res = await fetch(urls.generateIndividual.replace("USER_ID", userId), {
            method: "POST",
            headers: { "X-CSRFToken": csrfToken },
            body: new URLSearchParams({ selected_ids: seleccionados.join(",") })
          });

          if (!res.ok) throw new Error("Error en el servidor");
          const blob = await res.blob();

          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = "paquete_individual.zip";
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);
        } catch (err) {
          console.error(err);
          alert("❌ Error generando paquete individual.");
        }
      };
    }

    // Generar en Bloque (placeholder)
    const btnBloque = document.getElementById("generarBloque");
    if (btnBloque) {
      btnBloque.onclick = function () {
        alert("📦 Aquí se generarán constancias para TODOS los contratos seleccionados (en bloque).");
      };
    }

    // Ver/Editar contrato → abrir modal de FORM con datos cargados
    document.querySelectorAll(".ver-detalle").forEach(btn => {
      btn.addEventListener("click", async function () {
        const contratoId = this.dataset.id;
        try {
          const res = await fetch(`/documents/contrato/${contratoId}/`);
          const data = await res.json();
          if (!data.ok) throw new Error(data.error || "Error en servidor");

          const c = data.contrato;
          resetFormModalUI(); // limpio estado del form

          // Seteo de usuario_id en el form (lo tomo del modal de lista)
          const userId = document.getElementById('modal_usuario_id').value;
          document.getElementById('form_modal_usuario_id').value = userId;

          // Cargo campos
          document.getElementById("id_numero_contrato").value = c.numero_contrato || "";
          document.getElementById("id_fecha_inicio").value = c.fecha_inicio || "";
          document.getElementById("id_fecha_generacion").value = c.fecha_generacion || "";
          document.getElementById("id_fecha_fin").value = c.fecha_fin || "";
          document.getElementById("id_valor_pago").value = c.valor_pago || "";

          if (c.objeto) {
            wrapperObjeto.style.display = "";
            document.getElementById("id_objeto").value = c.objeto;
          }
          if (c.objetivos_especificos) {
            wrapperObjetivos.style.display = "";
            document.getElementById("id_objetivos_especificos").value = c.objetivos_especificos;
          }

          // contrato_id oculto para backend (edición)
          let hiddenId = document.getElementById("modal_contrato_id");
          if (!hiddenId) {
            hiddenId = document.createElement("input");
            hiddenId.type = "hidden";
            hiddenId.name = "contrato_id";
            hiddenId.id = "modal_contrato_id";
            form.appendChild(hiddenId);
          }
          hiddenId.value = contratoId;

          // Cambia texto del botón
          guardarBtnForm.textContent = "Actualizar";

          // Abre el modal de FORM
          formModal().show();

          alert("📑 Contrato cargado en el formulario para edición.");
        } catch (err) {
          console.error(err);
          alert("❌ Error cargando contrato");
        }
      });
    });
  }

  // ==============================
  // 3) A partir de ahora: dejamos que Bootstrap abra el modal (data-bs-*)
  //    y reaccionamos al evento 'show.bs.modal' para obtener el userId
  // ==============================
  if (listModalEl) {
    listModalEl.addEventListener('show.bs.modal', function (event) {
      // event.relatedTarget -> elemento que disparó el modal (el botón con data-bs-target)
      const trigger = event.relatedTarget;
      const userId = trigger ? trigger.dataset.userId : document.getElementById('modal_usuario_id').value;

      // Guardarlo en el hidden para que otras funciones lo usen
      document.getElementById('modal_usuario_id').value = userId;

      // Contenido inicial
      listModalBody.innerHTML = `<p class="text-muted">Cargando contratos...</p>`;

      // Refrescar contratos
      refrescarContratosCargados(userId);
    });
  }

  // ==============================
  // 4) Botón "Nuevo Contrato" (en modal de LISTA) → abre modal de FORM vacío
  // ==============================
  document.addEventListener("click", function (e) {
    if (e.target.closest("#nuevoContratoBtn")) {
      const userId = document.getElementById('modal_usuario_id').value;
      document.getElementById('form_modal_usuario_id').value = userId;

      resetFormModalUI();
      formModal().show();
    }
  });

  // ==============================
  // 5) UX del FORM: mostrar file input al digitar número
  // ==============================
  if (archivoInputWrapper) archivoInputWrapper.style.display = "none";
  if (wrapperObjeto) wrapperObjeto.style.display = "none";
  if (wrapperObjetivos) wrapperObjetivos.style.display = "none";
  if (guardarOtroBtn) guardarOtroBtn.style.display = "none";

  if (numeroContratoInput) {
    numeroContratoInput.addEventListener("input", function () {
      if (archivoInputWrapper) archivoInputWrapper.style.display = numeroContratoInput.value.length >= 5 ? "" : "none";
    });
  }

  // ==============================
  // 6) Guardar (botón azul) del FORM
  // ==============================
  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    if (formAlerts) formAlerts.style.display = 'none';
    if (formErrors) formErrors.innerHTML = '';

    const fd = new FormData(form);
    const res = await fetch(urls.contratoCreate, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      body: fd
    });

    const data = await res.json();
    if (!res.ok || !data.ok) {
      showFormErrors(data.errors || data);
      return;
    }

    // Refrescar LISTA en el modal de LISTA
    const userId = document.getElementById('form_modal_usuario_id').value;
    await refrescarContratosCargados(userId);

    // Si era actualización, dejo el form limpio para crear otro
    if (guardarBtnForm.textContent === "Actualizar") {
      resetFormModalUI();
    }

    alert("✅ Contrato guardado correctamente.");
    // Opcional: cerrar el modal tras guardar
    // bootstrap.Modal.getInstance(formModalEl).hide();
  });

  // ==============================
  // 7) Pre-llenar desde PDF (FORM)
  // ==============================
  if (archivoInput) {
    archivoInput.addEventListener("change", function () {
      const file = this.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append("archivo", file);

      fetch(urls.prefillContrato, {
        method: "POST",
        body: formData,
        headers: { "X-CSRFToken": csrfToken },
      })
        .then(res => res.json())
        .then(data => {
          if (data.ok) {
            const m = data.metadata;
            document.getElementById("id_valor_pago").value = m.valor_pago || "";
            document.getElementById("id_fecha_fin").value = m.plazo_fecha || "";

            if (m.objeto) {
              wrapperObjeto.style.display = "";
              document.getElementById("id_objeto").value = m.objeto;
            }
            if (m.objetivos_especificos) {
              wrapperObjetivos.style.display = "";
              document.getElementById("id_objetivos_especificos").value = m.objetivos_especificos;
            }

            guardarBtnForm.style.display = "none";
            guardarOtroBtn.style.display = "inline-block";
          } else {
            alert("⚠️ No se pudo procesar el PDF: " + data.error);
          }
        })
        .catch(err => {
          console.error(err);
          alert("⚠️ Error al enviar PDF para prellenar.");
        });
    });
  }

  // ==============================
  // 8) Habilitar edición manual campos largos (FORM)
  // ==============================
  const editObjetoBtn = document.getElementById("edit_objeto");
  if (editObjetoBtn) {
    editObjetoBtn.addEventListener("click", e => {
      e.preventDefault();
      document.getElementById("id_objeto").removeAttribute("readonly");
    });
  }
  const editObjetivosBtn = document.getElementById("edit_objetivos");
  if (editObjetivosBtn) {
    editObjetivosBtn.addEventListener("click", e => {
      e.preventDefault();
      document.getElementById("id_objetivos_especificos").removeAttribute("readonly");
    });
  }

  // ==============================
  // 9) Guardar y cargar otro (botón verde) del FORM
  // ==============================
  if (guardarOtroBtn) {
    guardarOtroBtn.addEventListener('click', async function () {
      if (formAlerts) formAlerts.style.display = 'none';
      if (formErrors) formErrors.innerHTML = '';

      const fd = new FormData(form);
      const res = await fetch(urls.contratoCreate, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
        body: fd
      });

      const data = await res.json();
      if (!res.ok || !data.ok) {
        showFormErrors(data.errors || data);
        return;
      }

      const userId = document.getElementById('form_modal_usuario_id').value;
      await refrescarContratosCargados(userId);

      resetFormModalUI(); // dejar listo para el próximo
      alert("Contrato guardado. Ahora puedes subir otro.");
    });
  }
});
