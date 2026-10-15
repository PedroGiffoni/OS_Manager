export interface Account {
  id: number;
  username: string;
  role: string;
  permissions: string[];
  csrf: string;
}
export interface Field {
  id: string;
  label: string;
  type: string;
  native_key?:
    | "id"
    | "title"
    | "status"
    | "supplier_id"
    | "sprint_id"
    | "estimated_minutes"
    | "used_minutes"
    | "approval"
    | null;
  options: string[];
  required_for: string[];
  visible_to: string[];
  editable_by: string[];
}
export interface Task {
  id: number;
  title: string;
  description: string;
  status: string;
  priority: number;
  due: string | null;
  supplier_id: number | null;
  sprint_id: number | null;
  estimated_minutes: number;
  used_minutes: number;
  hours_version: number;
  approval: string;
  approval_reason?: string;
  version: number;
  fields: Field[];
  values: Record<string, any>;
  rate_cents?: number | null;
  cost_cents?: number;
}
export interface Supplier {
  id: number;
  name: string;
  function: string;
  user_id: number | null;
  active: boolean;
  rate_cents?: number | null;
}
export interface Sprint {
  id: number;
  name: string;
  objective: string;
  starts: string;
  ends: string;
  state: string;
  owner_id: number;
  version: number;
}
export const stages: Record<string, string> = {
  backlog: "Backlog",
  todo: "A fazer",
  production: "Em produção",
  review: "Em revisão",
  done: "Concluído",
};
export const approvals: Record<string, string> = {
  pending: "Aguardando aprovação",
  approved: "Aprovado",
  rejected: "Rejeitado",
  resubmitted: "Reapresentado",
};
export const money = (cents: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    cents / 100,
  );
export function decimalToUnits(value: string, scale: number): number {
  if (scale === 60 && /^\d+:([0-5]\d)$/.test(value)) {
    const [hours, minutes] = value.split(":");
    return Number(hours) * 60 + Number(minutes);
  }
  const normalized = value.replace(",", ".");
  if (!/^\d+(\.\d{1,2})?$/.test(normalized))
    throw new Error("Informe um valor positivo com até duas casas decimais.");
  const [whole, fraction = ""] = normalized.split(".");
  const hundredths = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  if (scale === 100) return hundredths;
  if ((hundredths * scale) % 100)
    throw new Error("Informe horas equivalentes a minutos inteiros.");
  return (hundredths * scale) / 100;
}
let configuredTimezone = "America/Sao_Paulo";
export function setTimezone(value: string) {
  configuredTimezone = value;
}
export function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: configuredTimezone,
  }).format(new Date(value));
}
export function hourInput(minutes: number) {
  return minutes % 3 === 0
    ? String(minutes / 60)
    : Math.floor(minutes / 60) + ":" + String(minutes % 60).padStart(2, "0");
}
