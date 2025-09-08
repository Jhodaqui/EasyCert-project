$(document).ready(function () {
  // ==============================
  // 1. Modal de Crear Contrato
  // ==============================
  const modalEl = document.getElementById('contratoModal');
  const form = document.getElementById('contratoModalForm');
  const modalErrors = document.getElementById('modalErrors');
  const modalAlerts = document.getElementById('modalAlerts');
  const guardarOtroBtn = document.getElementById('guardarOtroBtn');
  const guardarBtn = document.querySelector("#contratoModal .btn-primary");

  // Referencias a campos
  const numeroContratoInput = document.getElementById("id_numero_contrato");
  const archivoInput = document.getElementById("id_archivo");
  const archivoInputWrapper = archivoInput.closest(".col-12");

  // Wrappers de campos extraídos
  const wrapperObjeto = document.getElementById("wrapper_objeto");
  const wrapperObjetivos = document.getElementById("wrapper_objetivos");

  // Lista temporal de contratos cargados
  const listaWrapper = document.getElementById("contratosCargadosWrapper");
  const lista = document.getElementById("contratosCargadosList");

  // Inicialmente ocultar campos dinámicos
  archivoInputWrapper.style.display = "none";
  wrapperObjeto.style.display = "none";
  wrapperObjetivos.style.display = "none";
  guardarOtroBtn.style.display = "none";
  if (listaWrapper) listaWrapper.style.display = "none";

  // Mostrar el campo de archivo solo si el número de contrato tiene al menos 5 caracteres
  numeroContratoInput.addEventListener("input", function () {
    archivoInputWrapper.style.display = numeroContratoInput.value.length >= 5 ? "" : "none";
  });

  // Abrir el modal y resetear el formulario
  document.querySelectorAll('.open-contrato-modal').forEach(btn => {
    btn.addEventListener('click', function () {
      const userId = this.dataset.userId;
      document.getElementById('modal_usuario_id').value = userId;
      form.reset();
      modalAlerts.style.display = 'none';

      // Ocultar vistas previas al abrir
      wrapperObjeto.style.display = "none";
      wrapperObjetivos.style.display = "none";
      archivoInputWrapper.style.display = "none";

      // Restaurar botones
      guardarBtn.style.display = "inline-block";
      guardarOtroBtn.style.display = "none";

      const modal = new bootstrap.Modal(modalEl);
      modal.show();
    });
  });

  // Mostrar errores en el modal
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
  // Función auxiliar: agregar contrato a la lista temporal
  // ==============================
  function enlistarContrato(fd) {
    if (!listaWrapper || !lista) return;

    listaWrapper.style.display = "";
    const li = document.createElement("li");
    li.classList.add("list-group-item", "d-flex", "justify-content-between", "align-items-center");
    li.innerHTML = `
      <span><strong>#${fd.get("numero_contrato") || "N/A"}</strong> - ${fd.get("objeto")?.substring(0,50) || "Contrato sin objeto"}...</span>
      <button class="btn btn-sm btn-danger removeContrato">✖</button>
    `;
    lista.appendChild(li);

    li.querySelector(".removeContrato").addEventListener("click", function () {
      li.remove();
      if (!lista.querySelector("li")) {
        listaWrapper.style.display = "none";
      }
    });
  }

  // ==============================
  // 1.1 Guardar contrato (azul)
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

    // Actualizar tabla
    const tableContainer = document.getElementById('contratosTable');
    if (tableContainer && data.table_html) {
      tableContainer.innerHTML = data.table_html;
    }

    // Enlistar contrato
    enlistarContrato(fd);

    alert("✅ Contrato guardado correctamente.");
  });

  // ==============================
  // 2. Prellenar Contrato con PDF
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

          // Cambiar flujo a múltiples contratos
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
  // 2.1 Habilitar edición manual
  // ==============================
  document.getElementById("edit_objeto").addEventListener("click", function (e) {
    e.preventDefault();
    const campo = document.getElementById("id_objeto");
    campo.removeAttribute("readonly");
    campo.focus();
  });

  document.getElementById("edit_objetivos").addEventListener("click", function (e) {
    e.preventDefault();
    const campo = document.getElementById("id_objetivos_especificos");
    campo.removeAttribute("readonly");
    campo.focus();
  });

  // ==============================
  // 2.2 Guardar y cargar otro (verde)
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

    enlistarContrato(fd);

    // Resetear para otro contrato
    form.reset();
    wrapperObjeto.style.display = "none";
    wrapperObjetivos.style.display = "none";
    archivoInputWrapper.style.display = "none";

    alert("Contrato guardado. Ahora puedes subir otro.");
  });

  // ==============================
  // 3. Ver Contratos del Usuario
  // ==============================
  document.querySelectorAll(".ver-contratos").forEach(btn => {
    btn.addEventListener("click", function () {
      const userId = this.dataset.user;
      const modalBody = document.getElementById("contratosModalBody");

      modalBody.innerHTML = "<p class='text-muted'>Cargando contratos...</p>";

      fetch(urls.verContratosBase + userId + "/")
        .then(res => res.json())
        .then(data => {
          modalBody.innerHTML = data.html;
        })
        .catch(err => {
          modalBody.innerHTML = "<p class='text-danger'>Error al cargar contratos.</p>";
        });
    });
  });

  // ==============================
  // 4. Filtros y Búsqueda
  // ==============================
  const filterSelects = document.querySelectorAll('.filter-select');
  const searchInput = document.getElementById('searchInput');
  const applyBtn = document.getElementById('applyFilters');
  const rows = document.querySelectorAll('.solicitud-row');

  function aplicarFiltros() {
    const tipoValue = document.getElementById('tipoFilter').value;
    const estadoValue = document.getElementById('estadoFilter').value;
    const fechaValue = document.getElementById('fechaFilter').value;
    const searchValue = searchInput.value.toLowerCase();

    const hoy = new Date();

    rows.forEach(row => {
      let mostrar = true;
      const tipo = row.getAttribute('data-tipo');
      const estado = row.getAttribute('data-estado');
      const fechaStr = row.getAttribute('data-fecha');
      const fecha = new Date(fechaStr);
      const textoFila = row.textContent.toLowerCase();

      if (tipoValue && tipo !== tipoValue) mostrar = false;
      if (estadoValue && estado !== estadoValue) mostrar = false;

      if (fechaValue === 'hoy') {
        const esHoy = fecha.getDate() === hoy.getDate() &&
          fecha.getMonth() === hoy.getMonth() &&
          fecha.getFullYear() === hoy.getFullYear();
        if (!esHoy) mostrar = false;
      } else if (fechaValue === 'semana') {
        const inicioSemana = new Date(hoy);
        inicioSemana.setDate(hoy.getDate() - hoy.getDay());
        if (fecha < inicioSemana) mostrar = false;
      } else if (fechaValue === 'mes') {
        if (fecha.getMonth() !== hoy.getMonth() || fecha.getFullYear() !== hoy.getFullYear()) {
          mostrar = false;
        }
      }

      if (searchValue && !textoFila.includes(searchValue)) {
        mostrar = false;
      }

      row.style.display = mostrar ? '' : 'none';
    });

    const visibles = document.querySelectorAll('.solicitud-row:not([style*="display: none"])');
    const badge = document.querySelector('.badge-count');
    if (badge) {
      badge.textContent = `${visibles.length} solicitudes`;
    }
  }

  applyBtn.addEventListener('click', function () {
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Aplicando...';
    setTimeout(() => {
      aplicarFiltros();
      this.innerHTML = '<i class="fas fa-check"></i> Filtros Aplicados';
      setTimeout(() => {
        this.innerHTML = '<i class="fas fa-filter"></i> Aplicar Filtros';
      }, 2000);
    }, 500);
  });

  searchInput.addEventListener('input', aplicarFiltros);
  filterSelects.forEach(select => select.addEventListener('change', aplicarFiltros));

  // ==============================
  // 5. Acciones sobre lista cargada
  // ==============================
  document.getElementById("generarIndividual").addEventListener("click", function () {
    alert("Aquí podrás seleccionar un contrato específico para generar constancia.");
  });

  document.getElementById("generarBloque").addEventListener("click", function () {
    alert("Aquí se generarán constancias para TODOS los contratos enlistados.");
  });
});
