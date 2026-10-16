import { useEffect, useRef } from "react";

export function HoursErrorDialog({
  message,
  returnFocus,
  onDismiss,
}: {
  message: string;
  returnFocus: HTMLElement | null;
  onDismiss: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = returnFocus;
    const element = dialog.current!;
    element.showModal();
    return () => {
      element.close();
      if (previous?.isConnected) previous.focus();
    };
  }, [returnFocus]);
  return (
    <dialog
      ref={dialog}
      className="hours-error-dialog"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="hours-error-title"
      aria-describedby="hours-error-description"
      onCancel={(event) => {
        event.preventDefault();
        onDismiss();
      }}
      onKeyDown={(event) => event.stopPropagation()}
    >
      <span className="hours-error-icon" aria-hidden="true">
        !
      </span>
      <h2 id="hours-error-title">Não foi possível mover a atividade</h2>
      <p id="hours-error-description">{message}</p>
      <p className="hours-error-help">
        O fornecedor responsável deve preencher e salvar as horas na atividade.
        O card permanece na etapa atual.
      </p>
      <button autoFocus onClick={onDismiss}>
        Entendi
      </button>
    </dialog>
  );
}
