let csrf = "";
const BOARD_STORAGE_KEY = "os-manager-active-board";
export function setActiveBoardId(identity: number | null) {
  if (identity === null) localStorage.removeItem(BOARD_STORAGE_KEY);
  else localStorage.setItem(BOARD_STORAGE_KEY, String(identity));
}
function boardHeaders(path: string): Record<string, string> {
  if (path === "/auth/login" || path === "/boards") return {};
  const identity = localStorage.getItem(BOARD_STORAGE_KEY);
  return identity ? { "X-Board-ID": identity } : {};
}
export function setCsrf(value: string) {
  csrf = value;
}
export async function api<T = any>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  const response = await fetch("/api/v1" + path, {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf, ...boardHeaders(path) },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      body.detail?.message ??
        (typeof body.detail === "string"
          ? body.detail
          : "Não foi possível concluir a operação."),
    );
  }
  return response.json();
}
export async function download(path: string) {
  const response = await fetch("/api/v1" + path, {
    credentials: "same-origin",
    headers: boardHeaders(path),
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail?.message ?? "Exportação indisponível.");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  const extension = path.split("?")[0].split("/").pop();
  anchor.download = "os-manager." + extension;
  anchor.click();
  URL.revokeObjectURL(url);
}
export async function downloadPost(path: string, data: unknown) {
  const response = await fetch("/api/v1" + path, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf, ...boardHeaders(path) },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail?.message ?? "Exportação indisponível.");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "gestao-de-demandas.ics";
  anchor.click();
  URL.revokeObjectURL(url);
}
export async function upload(path: string, file: File) {
  const data = new FormData();
  data.append("file", file);
  const response = await fetch("/api/v1" + path, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRF-Token": csrf, ...boardHeaders(path) },
    body: data,
  });
  if (!response.ok) {
    const body = await response.json();
    throw new Error(body.detail?.message ?? "Falha no envio do anexo.");
  }
  return response.json();
}

export async function uploadImage(path: string, file: File) {
  const response = await fetch("/api/v1" + path, {
    method: "PUT",
    credentials: "same-origin",
    headers: { "Content-Type": file.type, "X-CSRF-Token": csrf, ...boardHeaders(path) },
    body: file,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail?.message ?? "Não foi possível atualizar a foto.");
  }
  return response.json();
}
