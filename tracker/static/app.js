// Client detail page interactions: talk to the JSON API without full page reloads.
(() => {
  const head = document.querySelector("[data-client-id]");
  if (!head) return;
  const clientId = head.dataset.clientId;

  const api = async (url, method = "GET", body) => {
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  };

  const slug = (s) => s.toLowerCase().replace(/\s+/g, "-");
  const escapeHtml = (s) =>
    String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function renderClient(c) {
    document.getElementById("progress-val").textContent = `${c.progress}%`;
    document.getElementById("phase-val").textContent = c.phase;
    const badge = document.getElementById("health-badge");
    badge.textContent = c.health;
    badge.className = `badge h-${slug(c.health)}`;
  }

  // Tick / untick a task
  document.querySelectorAll("input[data-task-id]").forEach((box) => {
    box.addEventListener("change", async () => {
      try {
        const { task, client } = await api(`/api/tasks/${box.dataset.taskId}`, "PATCH", { done: box.checked });
        const li = box.closest("li");
        li.classList.toggle("done", task.done);
        li.classList.toggle("overdue", task.overdue);
        renderClient(client);
      } catch (err) {
        box.checked = !box.checked;
        alert(err.message);
      }
    });
  });

  // Add a custom task
  document.getElementById("task-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    if (!data.due_date) delete data.due_date;
    try {
      await api(`/api/clients/${clientId}/tasks`, "POST", data);
      location.reload();
    } catch (err) {
      alert(err.message);
    }
  });

  // Log a note / call / risk
  document.getElementById("note-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    try {
      const n = await api(`/api/clients/${clientId}/notes`, "POST", Object.fromEntries(new FormData(form)));
      document.getElementById("no-notes")?.remove();
      const li = document.createElement("li");
      li.className = `note-${n.kind}`;
      li.innerHTML = `<span class="small muted">${n.kind.toUpperCase()} · ${escapeHtml(n.author)} · just now</span><p>${escapeHtml(n.text)}</p>`;
      document.getElementById("notes").prepend(li);
      form.reset();
    } catch (err) {
      alert(err.message);
    }
  });

  // Mark client live
  document.getElementById("go-live-btn")?.addEventListener("click", async () => {
    if (!confirm("Mark this client as live today?")) return;
    await api(`/api/clients/${clientId}/go-live`, "POST", {});
    location.reload();
  });
})();
