"use strict";
const $ = id => document.getElementById(id);
const labels = {SOLICITADO:"Solicitado", EN_PROCESO:"En proceso", RESULTADO_CARGADO:"Resultado cargado", ENTREGADO:"Entregado", CANCELADO:"Cancelado"};
const roles = {medico:"Médico", laboratorista:"Laboratorista", paciente:"Paciente", admin:"Administrador"};
const base = "/api/lab";
let token = "", role = "", page = 1, busy = false;

function element(tag, value) {
  const node = document.createElement(tag);
  node.textContent = value;
  return node;
}

function signOut() {
  if ($("preview").open) $("preview").close();
  $("role").textContent = "";
  token = role = "";
  page = 1;
  $("desk").hidden = $("logout").hidden = true;
  $("access").hidden = false;
  $("modal").close();
  $("orders").replaceChildren();
  $("detail").replaceChildren();
  $("orderForm").reset();
  $("filter").value = $("token").value = $("notice").textContent = "";
}

async function run(action) {
  if (busy) return;
  busy = true;
  $("notice").textContent = $("formError").textContent = "";
  document.querySelector("main").inert = $("modal").inert = $("logout").disabled = true;
  try { await action(); }
  catch (err) {
    ($("modal").open ? $("formError") : $("notice")).textContent =
      err instanceof TypeError ? "No se pudo conectar. Comprueba la conexión y actualiza la bandeja." : err.message;
  } finally {
    document.querySelector("main").inert = $("modal").inert = $("logout").disabled = busy = false;
  }
}

async function request(path, options = {}, download = false) {
  const headers = {Authorization:"Bearer " + token};
  if (typeof options.body === "string") headers["Content-Type"] = "application/json";
  const res = await fetch(base + path, {...options, headers, cache:"no-store"});
  if (res.status === 401) {
    signOut();
    throw new Error("La credencial es inválida o ha caducado. Introduce un token vigente.");
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "No se pudo completar la operación (" + res.status + ").");
  }
  return download ? res.blob() : res.json();
}

function button(parent, title, action) {
  const btn = element("button", title);
  btn.onclick = () => run(action);
  parent.append(btn);
  return btn;
}

async function list() {
  const args = new URLSearchParams({page, page_size:10});
  if ($("filter").value) args.set("status", $("filter").value);
  const data = await request("/orders?" + args);
  const pages = Math.max(1, Math.ceil(data.total / 10));
  if (page > pages) { page = pages; return list(); }
  $("orders").replaceChildren();
  $("detail").replaceChildren(element("p", "Selecciona una orden para ver su detalle."));

  if (!data.items.length) {
    $("orders").append(element("p", "No hay órdenes para esta selección."));
    $("detail").replaceChildren(element("p", $("filter").value ? "Cambia el filtro para buscar otras órdenes." : "El detalle aparecerá aquí cuando haya una orden."));
  }
  for (const order of data.items) {
    const row = button($("orders"), "", () => detail(order.id));
    row.className = "row";
    row.dataset.id = order.id;
    row.append(element("strong", order.exam_type), element("small", [labels[order.status], order.priority, new Date(order.created_at).toLocaleDateString("es-CL")].join(" · ")));
  }
  $("pages").textContent = page + " de " + pages;
  $("prev").disabled = page <= 1;
  $("next").disabled = page >= pages;
}

async function detail(id) {
  const order = await request("/orders/" + id);

  document.querySelectorAll(".row").forEach(row => row.setAttribute("aria-pressed", String(row.dataset.id === id)));
  const panel = $("detail");
  panel.replaceChildren(element("h2",order.exam_type));
  const fields = element("dl","");
  for (const [key,value] of Object.entries({Estado:labels[order.status], Prioridad:order.priority, Paciente:order.patient_id, Orden:id, "Notas clínicas":order.clinical_notes || "Sin notas"}))
    fields.append(element("dt",key),element("dd",value));
  panel.append(fields);
  const path = "/orders/" + id;
  async function change(method, suffix, body) {
    await request(path + suffix, {method, body});
    await list();
    if ([...document.querySelectorAll(".row")].some(row => row.dataset.id === id)) await detail(id);
    $("notice").textContent = "Orden actualizada.";
  }
  if (role === "medico" && order.status === "SOLICITADO") button(panel,"Cancelar orden",async () => {
    if (confirm("¿Cancelar esta orden de laboratorio?")) await change("DELETE","");
  });
  if (role === "laboratorista") {
    const transitions = {SOLICITADO:["EN_PROCESO","CANCELADO"], EN_PROCESO:["CANCELADO"], RESULTADO_CARGADO:["ENTREGADO"]};
    for (const status of transitions[order.status] || []) {
      button(panel,"Marcar como " + labels[status].toLowerCase(), async () => {
        if (status !== "CANCELADO" || confirm("¿Cancelar esta orden?")) await change("PATCH","/status",JSON.stringify({status}));
      });
    }
    if (!["ENTREGADO","CANCELADO"].includes(order.status)) {
      const label = element("label","Informe en PDF, JPEG o PNG");
      const file = document.createElement("input");
      file.type = "file"; file.accept = ".pdf,.jpg,.jpeg,.png";
      label.append(file); panel.append(label);
      button(panel,"Adjuntar informe",async () => {
        if (!file.files.length) throw new Error("Selecciona el archivo que quieres adjuntar.");
        const data = new FormData();
        data.append("file",file.files[0]);
        await change("POST","/results",data);
      });
    }
  }
  panel.append(element("h3","Informes"));
  const results = (await request("/patients/" + order.patient_id + "/results")).filter(r => r.order_id === id);
  if (!results.length) panel.append(element("p","Todavía no hay informes adjuntos."));
  for (const report of results) {
    const item = element("div","");
    item.className = "report";
    item.append(element("strong",report.original_filename));
    panel.append(item);
    const fetchReport = () => request("/results/" + report.id + "/download",{},true);
    button(item,"Ver informe",async () => {
      const viewer = await import("/assets/report.js");
      await viewer.openReport(await fetchReport(), report.original_filename);
    }).setAttribute("aria-label","Ver informe " + report.original_filename);
    button(item,"Descargar " + report.original_filename,async () => {
      const viewer = await import("/assets/report.js");
      viewer.download(await fetchReport(), report.original_filename);
    });
  }
}

$("filter").add(new Option("Todos los estados",""));
for (const [key,label] of Object.entries(labels)) $("filter").add(new Option(label,key));
$("login").onsubmit = event => {
  event.preventDefault();
  run(async () => {
    token = $("token").value.trim().replace(/^Bearer\s+/i,"");
    await list(); // La API verifica la firma antes de mostrar el espacio de trabajo.
    const payload = token.split(".")[1].replace(/-/g,"+").replace(/_/g,"/");
    role = JSON.parse(atob(payload)).role;
    $("role").textContent = "Sesión de " + roles[role].toLowerCase();
    $("create").hidden = role !== "medico";
    $("access").hidden = true; $("desk").hidden = $("logout").hidden = false;
    $("token").value = "";
  });
};
$("logout").onclick = signOut;
$("filter").onchange = () => run(async () => { page = 1; await list(); });
$("prev").onclick = () => run(async () => { page--; await list(); });
$("next").onclick = () => run(async () => { page++; await list(); });
$("refresh").onclick = () => run(list);
$("create").onclick = () => { $("formError").textContent = ""; $("modal").showModal(); };
$("close").onclick = () => $("modal").close();
$("orderForm").onsubmit = event => {
  event.preventDefault();
  run(async () => {
    const data = Object.fromEntries(new FormData($("orderForm")));
    const created = await request("/orders",{method:"POST",body:JSON.stringify(data)});
    $("modal").close(); $("orderForm").reset(); page = 1; $("filter").value = "";
    await list(); await detail(created.id);
    $("notice").textContent = "Orden creada.";
  });
};


