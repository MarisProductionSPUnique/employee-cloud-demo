"use strict";

const state = {
  employees: [],
  editingId: null,
  deletingId: null,
  requestTrail: [],
  latestRequestId: "",
};

const elements = {
  form: document.querySelector("#employeeForm"),
  formTitle: document.querySelector("#formTitle"),
  employeeId: document.querySelector("#employeeId"),
  employeeCode: document.querySelector("#employeeCode"),
  employeeName: document.querySelector("#employeeName"),
  employeeEmail: document.querySelector("#employeeEmail"),
  employeeDepartment: document.querySelector("#employeeDepartment"),
  employeeRole: document.querySelector("#employeeRole"),
  employeeStatus: document.querySelector("#employeeStatus"),
  employeeNotes: document.querySelector("#employeeNotes"),
  employeeRows: document.querySelector("#employeeRows"),
  employeeCount: document.querySelector("#employeeCount"),
  emptyState: document.querySelector("#emptyState"),
  searchInput: document.querySelector("#searchInput"),
  saveButton: document.querySelector("#saveButton"),
  cancelEdit: document.querySelector("#cancelEdit"),
  notice: document.querySelector("#notice"),
  apiStatus: document.querySelector("#apiStatus"),
  apiDot: document.querySelector("#apiDot"),
  databaseStatus: document.querySelector("#databaseStatus"),
  databaseDot: document.querySelector("#databaseDot"),
  latestRequestId: document.querySelector("#latestRequestId"),
  latestResponse: document.querySelector("#latestResponse"),
  copyRequestId: document.querySelector("#copyRequestId"),
  healthButton: document.querySelector("#healthButton"),
  traceRows: document.querySelector("#traceRows"),
  clearTrail: document.querySelector("#clearTrail"),
  deleteDialog: document.querySelector("#deleteDialog"),
  deleteMessage: document.querySelector("#deleteMessage"),
  confirmDelete: document.querySelector("#confirmDelete"),
};

function makeRequestId() {
  const now = new Date();
  const stamp = now.toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
  const random = Math.random().toString(36).slice(2, 7).toUpperCase();
  return `CLASS-${stamp}-${random}`;
}

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = value ?? "";
  return span.innerHTML;
}

function showNotice(message, isError = false) {
  elements.notice.textContent = message;
  elements.notice.classList.toggle("is-error", isError);
  elements.notice.hidden = false;
  window.clearTimeout(showNotice.timer);
  showNotice.timer = window.setTimeout(() => {
    elements.notice.hidden = true;
  }, 5500);
}

function setLatestRequest(requestId, status) {
  state.latestRequestId = requestId || "Not returned";
  elements.latestRequestId.textContent = state.latestRequestId;
  elements.latestRequestId.title = state.latestRequestId;
  elements.latestResponse.textContent = status ? `HTTP ${status}` : "Network error";
  elements.copyRequestId.disabled = !requestId;
}

function addTrail({ method, endpoint, status, duration, requestId }) {
  state.requestTrail.unshift({
    time: new Date().toLocaleTimeString(),
    method,
    endpoint,
    status,
    duration,
    requestId,
  });
  state.requestTrail = state.requestTrail.slice(0, 12);
  renderTrail();
}

function renderTrail() {
  if (!state.requestTrail.length) {
    elements.traceRows.innerHTML = '<tr class="trace-placeholder"><td colspan="6">Requests will appear here.</td></tr>';
    return;
  }

  elements.traceRows.innerHTML = state.requestTrail.map((item) => {
    const family = item.status === 0 || item.status >= 500 ? "5xx" : item.status >= 400 ? "4xx" : "2xx";
    return `
      <tr>
        <td>${escapeHtml(item.time)}</td>
        <td>${escapeHtml(item.method)}</td>
        <td>${escapeHtml(item.endpoint)}</td>
        <td><span class="http-status status-${family}">${escapeHtml(String(item.status || "ERR"))}</span></td>
        <td>${escapeHtml(`${item.duration} ms`)}</td>
        <td title="${escapeHtml(item.requestId)}">${escapeHtml(item.requestId)}</td>
      </tr>`;
  }).join("");
}

async function apiRequest(endpoint, options = {}) {
  const method = options.method || "GET";
  const clientRequestId = makeRequestId();
  const started = performance.now();
  let response;
  let payload;

  try {
    response = await fetch(endpoint, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": clientRequestId,
        ...(options.headers || {}),
      },
    });
    try {
      payload = await response.json();
    } catch (_error) {
      payload = { success: false, error: { message: "The server returned a non-JSON response." } };
    }

    const requestId = response.headers.get("X-Request-ID") || payload.request_id || clientRequestId;
    const duration = Math.round(performance.now() - started);
    setLatestRequest(requestId, response.status);
    addTrail({ method, endpoint, status: response.status, duration, requestId });

    if (!response.ok) {
      const error = new Error(payload.error?.message || `Request failed with HTTP ${response.status}.`);
      error.payload = payload;
      error.status = response.status;
      throw error;
    }
    return payload;
  } catch (error) {
    if (!response) {
      const duration = Math.round(performance.now() - started);
      setLatestRequest(clientRequestId, null);
      addTrail({ method, endpoint, status: 0, duration, requestId: clientRequestId });
    }
    throw error;
  }
}

async function checkHealth(showMessage = false) {
  elements.apiStatus.textContent = "Checking";
  elements.databaseStatus.textContent = "Checking";
  elements.apiDot.className = "status-dot is-checking";
  elements.databaseDot.className = "status-dot is-checking";
  try {
    const result = await apiRequest("/api/health");
    elements.apiStatus.textContent = "Healthy";
    elements.databaseStatus.textContent = `${result.database_type} connected`;
    elements.apiDot.className = "status-dot is-up";
    elements.databaseDot.className = "status-dot is-up";
    if (showMessage) showNotice(`Health check passed in ${result.response_time_ms} ms.`);
  } catch (error) {
    elements.apiStatus.textContent = error.status ? "Degraded" : "Unavailable";
    elements.databaseStatus.textContent = "Connection failed";
    elements.apiDot.className = "status-dot is-down";
    elements.databaseDot.className = "status-dot is-down";
    if (showMessage) showNotice(error.message, true);
  }
}

async function loadEmployees(query = "") {
  const endpoint = query ? `/api/employees?q=${encodeURIComponent(query)}` : "/api/employees";
  try {
    const result = await apiRequest(endpoint);
    state.employees = result.data;
    renderEmployees();
  } catch (error) {
    showNotice(`Could not load employees: ${error.message}`, true);
  }
}

function renderEmployees() {
  elements.employeeCount.textContent = String(state.employees.length);
  elements.emptyState.hidden = state.employees.length !== 0;

  elements.employeeRows.innerHTML = state.employees.map((employee) => {
    const statusClass = employee.status.toLowerCase().replaceAll(" ", "-");
    return `
      <tr>
        <td>
          <span class="employee-main">${escapeHtml(employee.name)}</span>
          <span class="employee-sub">${escapeHtml(employee.employee_code)} · ${escapeHtml(employee.email)}</span>
        </td>
        <td>
          <span class="department-line">${escapeHtml(employee.department)}</span>
          <span class="role-line">${escapeHtml(employee.role)}</span>
        </td>
        <td><span class="status-pill status-${statusClass}">${escapeHtml(employee.status)}</span></td>
        <td>
          <div class="row-actions">
            <button class="action-button" type="button" data-action="edit" data-id="${employee.id}">Edit</button>
            <button class="action-button is-delete" type="button" data-action="delete" data-id="${employee.id}">Delete</button>
          </div>
        </td>
      </tr>`;
  }).join("");
}

function clearFieldErrors() {
  document.querySelectorAll(".field-error").forEach((element) => {
    element.textContent = "";
  });
  elements.form.querySelectorAll("[aria-invalid]").forEach((element) => {
    element.removeAttribute("aria-invalid");
  });
}

function displayFieldErrors(errors = {}) {
  Object.entries(errors).forEach(([field, message]) => {
    const target = document.querySelector(`[data-error-for="${field}"]`);
    const input = elements.form.elements[field];
    if (target) target.textContent = message;
    if (input) input.setAttribute("aria-invalid", "true");
  });
}

function formPayload() {
  const data = new FormData(elements.form);
  return Object.fromEntries(data.entries());
}

function resetForm() {
  state.editingId = null;
  elements.form.reset();
  elements.employeeId.value = "";
  elements.employeeStatus.value = "Active";
  elements.formTitle.textContent = "Add employee";
  elements.saveButton.textContent = "Create employee";
  elements.cancelEdit.hidden = true;
  clearFieldErrors();
}

function startEdit(employeeId) {
  const employee = state.employees.find((item) => item.id === employeeId);
  if (!employee) return;

  state.editingId = employee.id;
  elements.employeeId.value = employee.id;
  elements.employeeCode.value = employee.employee_code;
  elements.employeeName.value = employee.name;
  elements.employeeEmail.value = employee.email;
  elements.employeeDepartment.value = employee.department;
  elements.employeeRole.value = employee.role;
  elements.employeeStatus.value = employee.status;
  elements.employeeNotes.value = employee.notes;
  elements.formTitle.textContent = `Edit ${employee.employee_code}`;
  elements.saveButton.textContent = "Update employee";
  elements.cancelEdit.hidden = false;
  clearFieldErrors();
  elements.employeeCode.focus();
  window.scrollTo({ top: 80, behavior: "smooth" });
}

async function saveEmployee(event) {
  event.preventDefault();
  clearFieldErrors();
  const editing = Boolean(state.editingId);
  const endpoint = editing ? `/api/employees/${state.editingId}` : "/api/employees";
  const method = editing ? "PUT" : "POST";

  elements.saveButton.disabled = true;
  elements.saveButton.textContent = editing ? "Updating…" : "Creating…";
  try {
    const result = await apiRequest(endpoint, {
      method,
      body: JSON.stringify(formPayload()),
    });
    showNotice(result.message);
    resetForm();
    await loadEmployees(elements.searchInput.value.trim());
  } catch (error) {
    displayFieldErrors(error.payload?.error?.fields);
    showNotice(`${error.message} Request ID: ${state.latestRequestId}`, true);
  } finally {
    elements.saveButton.disabled = false;
    elements.saveButton.textContent = state.editingId ? "Update employee" : "Create employee";
  }
}

function requestDelete(employeeId) {
  const employee = state.employees.find((item) => item.id === employeeId);
  if (!employee) return;
  state.deletingId = employee.id;
  elements.deleteMessage.textContent = `${employee.employee_code} – ${employee.name} will be removed from the database.`;
  elements.deleteDialog.showModal();
}

async function deleteEmployee() {
  const employeeId = state.deletingId;
  state.deletingId = null;
  if (!employeeId) return;

  try {
    const result = await apiRequest(`/api/employees/${employeeId}`, { method: "DELETE" });
    showNotice(result.message);
    if (state.editingId === employeeId) resetForm();
    await loadEmployees(elements.searchInput.value.trim());
  } catch (error) {
    showNotice(`${error.message} Request ID: ${state.latestRequestId}`, true);
  }
}

async function runTeachingDemo(kind) {
  const demos = {
    health: { endpoint: "/api/health", success: "HTTP 200: API and database are healthy." },
    missing: { endpoint: "/api/not-found" },
    error: { endpoint: "/api/demo/error" },
    slow: { endpoint: "/api/demo/slow?seconds=3", success: "Slow request completed. Compare its duration with other requests." },
  };
  const demo = demos[kind];
  if (!demo) return;

  try {
    const result = await apiRequest(demo.endpoint);
    showNotice(demo.success || result.message || "Request completed.");
  } catch (error) {
    showNotice(`Expected HTTP ${error.status}: ${error.message} Request ID: ${state.latestRequestId}`, false);
  }
}

elements.form.addEventListener("submit", saveEmployee);
elements.cancelEdit.addEventListener("click", resetForm);
elements.healthButton.addEventListener("click", () => checkHealth(true));
elements.copyRequestId.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(state.latestRequestId);
    showNotice("Request ID copied.");
  } catch (_error) {
    showNotice("Select and copy the request ID manually.", true);
  }
});

elements.employeeRows.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const employeeId = Number(button.dataset.id);
  if (button.dataset.action === "edit") startEdit(employeeId);
  if (button.dataset.action === "delete") requestDelete(employeeId);
});

elements.deleteDialog.addEventListener("close", () => {
  if (elements.deleteDialog.returnValue === "confirm") deleteEmployee();
  else state.deletingId = null;
});

let searchTimer;
elements.searchInput.addEventListener("input", () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => loadEmployees(elements.searchInput.value.trim()), 300);
});

document.querySelectorAll("[data-demo]").forEach((button) => {
  button.addEventListener("click", () => runTeachingDemo(button.dataset.demo));
});

elements.clearTrail.addEventListener("click", () => {
  state.requestTrail = [];
  renderTrail();
});

async function initialise() {
  await checkHealth(false);
  await loadEmployees();
}

initialise();
