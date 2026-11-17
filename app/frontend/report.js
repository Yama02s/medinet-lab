const $ = id => document.getElementById(id);
const dialog = $("preview");
const canvas = dialog.querySelector("canvas");
let session;

export function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}

async function drawPage(view, number) {
  if (session !== view || view.rendering) return;
  view.rendering = true;
  $("previousReport").disabled = $("nextReport").disabled = true;
  $("previewStatus").textContent = "Cargando página…";
  try {
    const page = await view.pdf.getPage(number);
    if (session !== view) return;
    const size = page.getViewport({scale: 1});
    const viewport = page.getViewport({scale: Math.min(2, 1800 / Math.max(size.width, size.height))});
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    await page.render({canvasContext: canvas.getContext("2d"), viewport}).promise;
    if (session !== view) return;
    canvas.hidden = false;
    view.page = number;
    $("pageNumber").textContent = number + " de " + view.pdf.numPages;
    $("previewStatus").textContent = "";
    $("pdfPages").hidden = false;
  } catch {
    if (session === view) showFallback();
  } finally {
    view.rendering = false;
    if (session === view) {
      $("previousReport").disabled = view.page <= 1;
      $("nextReport").disabled = view.page >= view.pdf.numPages;
    }
  }
}

function showFallback() {
  canvas.hidden = true;
  $("previewStatus").textContent = "No se pudo mostrar el informe. Puedes descargarlo y abrirlo en tu equipo.";
}

function release() {
  const old = session;
  session = null;
  if (old?.task) old.task.destroy().catch(() => {});
  canvas.width = canvas.height = 0;
  canvas.hidden = $("pdfPages").hidden = true;
  $("previewName").textContent = $("previewStatus").textContent = "";
}

dialog.addEventListener("close", release);
$("closePreview").onclick = () => dialog.close();
$("saveReport").onclick = () => { if (session) download(session.blob, session.name); };
$("previousReport").onclick = () => drawPage(session, session.page - 1);
$("nextReport").onclick = () => drawPage(session, session.page + 1);

export async function openReport(blob, name) {
  const view = {blob, name, page:1};
  session = view;
  $("previewName").textContent = name;
  $("previewStatus").textContent = "Preparando vista previa…";
  dialog.showModal();
  try {
    if (blob.type === "application/pdf") {
      const pdfjs = await import("./pdfjs/pdf.min.mjs");
      const data = await blob.arrayBuffer();
      if (view !== session) return;
      pdfjs.GlobalWorkerOptions.workerSrc = "/assets/pdfjs/pdf.worker.min.mjs";
      view.task = pdfjs.getDocument({data, isEvalSupported:false, useWasm:false,
        disableFontFace:true, useSystemFonts:true, useWorkerFetch:false,
        cMapUrl:"/assets/pdfjs/cmaps/", cMapPacked:true,
        standardFontDataUrl:"/assets/pdfjs/standard_fonts/", wasmUrl:"/assets/pdfjs/wasm/"});
      view.pdf = await view.task.promise;
      if (view === session) await drawPage(view, 1);
    } else if (["image/jpeg", "image/png"].includes(blob.type)) {
      const bitmap = await createImageBitmap(blob);
      try {
        if (view !== session) return;
        const scale = Math.min(1, 2400 / Math.max(bitmap.width, bitmap.height));
        canvas.width = Math.max(1, Math.round(bitmap.width * scale));
        canvas.height = Math.max(1, Math.round(bitmap.height * scale));
        canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
        canvas.hidden = false;
        $("previewStatus").textContent = "";
      } finally { bitmap.close(); }
    } else { showFallback(); }
  } catch {
    if (view === session) showFallback();
  }
}
