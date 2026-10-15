let csrf = "";
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
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
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
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail?.message ?? "Exportação indisponível.");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "os-manager." + (path.includes("/xlsx") ? "xlsx" : "pdf");
  anchor.click();
  URL.revokeObjectURL(url);
}
export async function upload(path: string, file: File) {
  const data = new FormData();
  data.append("file", file);
  const response = await fetch("/api/v1" + path, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRF-Token": csrf },
    body: data,
  });
  if (!response.ok) {
    const body = await response.json();
    throw new Error(body.detail?.message ?? "Falha no envio do anexo.");
  }
  return response.json();
}
