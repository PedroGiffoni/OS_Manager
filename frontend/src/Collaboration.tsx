import { formatTimestamp } from "./types";
import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, upload } from "./api";
import { Label, type Run } from "./App";
export function Collaboration({
  identity,
  readOnly,
  run,
}: {
  identity: number;
  readOnly: boolean;
  run: Run;
}) {
  const [comment, setComment] = useState("");
  const comments = useQuery({
    queryKey: ["comments", identity],
    queryFn: () => api<any[]>(`/tasks/${identity}/comments`),
  });
  const attachments = useQuery({
    queryKey: ["attachments", identity],
    queryFn: () => api<any[]>(`/tasks/${identity}/attachments`),
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    run(async () => {
      await api(`/tasks/${identity}/comments`, "POST", { body: comment });
      setComment("");
    });
  };
  return (
    <>
      <section className="inline-form">
        <h3>Anexos</h3>
        <p>PDF, PNG, JPEG ou texto UTF-8. Até 5 MiB por arquivo.</p>
        <ul>
          {attachments.data?.map((file) => (
            <li key={file.id}>
              <a href={"/api/v1/attachments/" + file.id}>{file.name}</a>{" "}
              <small>
                {Math.ceil(file.size / 1024)} KiB ·{" "}
                {formatTimestamp(file.created_at)}
              </small>
            </li>
          ))}
        </ul>
        {!readOnly && (
          <Label title="Enviar anexo">
            <input
              type="file"
              accept="application/pdf,image/png,image/jpeg,text/plain"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file)
                  run(() => upload(`/tasks/${identity}/attachments`, file));
                event.target.value = "";
              }}
            />
          </Label>
        )}
        {attachments.error && <p>{attachments.error.message}</p>}
      </section>
      <section className="inline-form">
        <h3>Comentários</h3>
        {comments.data?.map((row) => (
          <article key={row.id}>
            <p style={{ whiteSpace: "pre-wrap" }}>{row.body}</p>
            <small>
              Usuário {row.author_id} · {formatTimestamp(row.created_at)}
            </small>
          </article>
        ))}
        {!readOnly && (
          <form onSubmit={submit}>
            <Label title="Novo comentário">
              <textarea
                required
                maxLength={5000}
                value={comment}
                onChange={(event) => setComment(event.target.value)}
              />
            </Label>
            <button>Adicionar comentário</button>
          </form>
        )}
        {comments.error && <p>{comments.error.message}</p>}
      </section>
    </>
  );
}
