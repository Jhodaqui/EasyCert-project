$(document).ready(function () {
  // ==============================
  // 1. Modal de Crear/Editar Contrato
  // ==============================
  const modalEl = document.getElementById('contratoModal');
  const form = document.getElementById('contratoModalForm');
  const modalErrors = document.getElementById('modalErrors');
  const modalAlerts = document.getElementById('modalAlerts');
  const guardarOtroBtn = document.getElementById('guardarOtroBtn');
  const guardarBtn = document.querySelector("#contratoModal .btn-primary");

  const numeroContratoInput = document.getElementById("id_numero_contrato");
  const archivoInput = document.getElementById("id_archivo");
  const archivoInputWrapper = archivoInput.closest(".col-12");

  const wrapperObjeto = document.getElementById("wrapper_objeto");
  const wrapperObjetivos = document.getElementById("wrapper_objetivos");

  // ==============================
  // Función: refrescar lista de contratos
  // ==============================
  async function refrescarContratosCargados(userId) {
    try {
      const res = await fetch(urls.verContratosBase + userId + "/");
      const data = await res.json();

      let listaWrapper = document.getElementById("contratosCargadosWrapper");
      if (!listaWrapper) {
        listaWrapper = document.createElement("div");
        listaWrapper.id = "contratosCargadosWrapper";
        listaWrapper.classList.add("mt-4");
        form.querySelector(".modal-body .row").appendChild(listaWrapper);
      }

      listaWrapper.innerHTML = `
        <h6>Contratos del usuario:</h6>
        <div class="table-responsive">${data.html}</div>
      `;

      bindAccionesContratos(userId);
    } catch (err) {
      console.error("Error refrescando contratos:", err);
    }
  }

  // ==============================
  // Acciones en tabla de contratos
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

    // Generar Individual
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

    // Generar en Bloque
    const btnBloque = document.getElementById("generarBloque");
    if (btnBloque) {
      btnBloque.onclick = function () {
        alert("📦 Aquí se generarán constancias para TODOS los contratos seleccionados (en bloque).");
      };
    }

    // Ver contrato (modo edición)
    document.querySelectorAll(".ver-detalle").forEach(btn => {
      btn.addEventListener("click", async function () {
        const contratoId = this.dataset.id;
        try {
          const res = await fetch(`/documents/contrato/${contratoId}/`);
          const data = await res.json();
          if (!data.ok) throw new Error(data.error || "Error en servidor");

          const c = data.contrato;
          document.getElementById("id_numero_contrato").value = c.numero_contrato;
          document.getElementById("id_fecha_inicio").value = c.fecha_inicio;
          document.getElementById("id_fecha_generacion").value = c.fecha_generacion;
          document.getElementById("id_fecha_fin").value = c.fecha_fin;
          document.getElementById("id_valor_pago").value = c.valor_pago;

          if (c.objeto) {
            wrapperObjeto.style.display = "";
            document.getElementById("id_objeto").value = c.objeto;
          }
          if (c.objetivos_especificos) {
            wrapperObjetivos.style.display = "";
            document.getElementById("id_objetivos_especificos").value = c.objetivos_especificos;
          }

          // Guardamos contrato_id oculto para que backend sepa que es edición
          let hiddenId = document.getElementById("modal_contrato_id");
          if (!hiddenId) {
            hiddenId = document.createElement("input");
            hiddenId.type = "hidden";
            hiddenId.name = "contrato_id";
            hiddenId.id = "modal_contrato_id";
            form.appendChild(hiddenId);
          }
          hiddenId.value = contratoId;

          // Cambiamos el texto del botón azul a "Actualizar"
          guardarBtn.textContent = "Actualizar";

          this.closest("tr").remove();
          alert("📑 Contrato cargado en el formulario para edición.");
        } catch (err) {
          console.error(err);
          alert("❌ Error cargando contrato");
        }
      });
    });
  }

  // ==============================
  // Inicialización modal
  // ==============================
  archivoInputWrapper.style.display = "none";
  wrapperObjeto.style.display = "none";
  wrapperObjetivos.style.display = "none";
  guardarOtroBtn.style.display = "none";

  numeroContratoInput.addEventListener("input", function () {
    archivoInputWrapper.style.display = numeroContratoInput.value.length >= 5 ? "" : "none";
  });

  document.querySelectorAll('.open-contrato-modal').forEach(btn => {
    btn.addEventListener('click', function () {
      const userId = this.dataset.userId;
      document.getElementById('modal_usuario_id').value = userId;
      form.reset();

      // Reset del modal
      modalAlerts.style.display = 'none';
      wrapperObjeto.style.display = "none";
      wrapperObjetivos.style.display = "none";
      archivoInputWrapper.style.display = "none";
      guardarBtn.style.display = "inline-block";
      guardarBtn.textContent = "Guardar";  // 👈 reset a Guardar
      guardarOtroBtn.style.display = "none";

      // Eliminar contrato_id si había
      const hiddenId = document.getElementById("modal_contrato_id");
      if (hiddenId) hiddenId.remove();

      const modal = new bootstrap.Modal(modalEl);
      modal.show();

      refrescarContratosCargados(userId);
    });
  });

  function showErrors(errs) {
    modalErrors.innerHTML = '';
    for (const k in errs) {
      const msgs = errs[k];
      if (Array.isArray(msgs)) {
        msgs.forEach(m => modalErrors.innerHTML += `<div>${k}: ${m}</div>`);
      } else {
        modalErrors.innerHTML += `<div>${k}: ${msgs}</div>`;
      }
    }
    modalAlerts.style.display = 'block';
  }

  // ==============================
  // Guardar contrato (azul)
  // ==============================
  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    modalAlerts.style.display = 'none';
    modalErrors.innerHTML = '';

    const fd = new FormData(form);
    const res = await fetch(urls.contratoCreate, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      body: fd
    });

    const data = await res.json();
    if (!res.ok || !data.ok) {
      showErrors(data.errors || data);
      return;
    }

    const tableContainer = document.getElementById('contratosTable');
    if (tableContainer && data.table_html) {
      tableContainer.innerHTML = data.table_html;
    }

    const userId = document.getElementById('modal_usuario_id').value;
    await refrescarContratosCargados(userId);

    // ✅ Nuevo comportamiento si era actualización
    if (guardarBtn.textContent === "Actualizar") {
      form.reset();
      wrapperObjeto.style.display = "none";
      wrapperObjetivos.style.display = "none";
      archivoInputWrapper.style.display = "none";

      const hiddenId = document.getElementById("modal_contrato_id");
      if (hiddenId) hiddenId.remove();

      guardarBtn.textContent = "Guardar"; // volver a modo normal
    }

    alert("✅ Contrato guardado correctamente.");
  });

  // ==============================
  // Prellenar con PDF
  // ==============================
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

          guardarBtn.style.display = "none";
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

  // ==============================
  // Habilitar edición manual
  // ==============================
  document.getElementById("edit_objeto").addEventListener("click", e => {
    e.preventDefault();
    document.getElementById("id_objeto").removeAttribute("readonly");
  });
  document.getElementById("edit_objetivos").addEventListener("click", e => {
    e.preventDefault();
    document.getElementById("id_objetivos_especificos").removeAttribute("readonly");
  });

  // ==============================
  // Guardar y cargar otro (verde)
  // ==============================
  guardarOtroBtn.addEventListener('click', async function () {
    modalAlerts.style.display = 'none';
    modalErrors.innerHTML = '';

    const fd = new FormData(form);
    const res = await fetch(urls.contratoCreate, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      body: fd
    });

    const data = await res.json();
    if (!res.ok || !data.ok) {
      showErrors(data.errors || data);
      return;
    }

    const tableContainer = document.getElementById('contratosTable');
    if (tableContainer && data.table_html) {
      tableContainer.innerHTML = data.table_html;
    }

    const userId = document.getElementById('modal_usuario_id').value;
    await refrescarContratosCargados(userId);

    form.reset();
    wrapperObjeto.style.display = "none";
    wrapperObjetivos.style.display = "none";
    archivoInputWrapper.style.display = "none";

    alert("Contrato guardado. Ahora puedes subir otro.");
  });
});
