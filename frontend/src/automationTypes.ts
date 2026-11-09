export type CapacityUser = { id: number; username: string; role: string };

export type WorkflowAction = {
  action: "set_priority" | "add_label" | "remove_label" | "add_comment" | "set_due_after_days" | "assign_internal_user" | "add_watcher" | "set_custom_fields";
  config: Record<string, unknown>;
};

export type AutomationRule = {
  id: number;
  name: string;
  trigger: string;
  schedule_time: string | null;
  schedule_frequency: "daily" | "weekly";
  schedule_weekdays: number[];
  conditions: Record<string, unknown>;
  action: string;
  config: Record<string, any>;
  actions: WorkflowAction[];
  enabled: boolean;
};

export type AutomationRuleDraft = {
  name: string;
  trigger: string;
  schedule_time: string;
  schedule_frequency: "daily" | "weekly";
  schedule_weekdays: number[];
  action: WorkflowAction["action"];
  priority: string;
  label: string;
  comment: string;
  due_days: string;
  assignee_user: string;
  custom_field_values: string;
  assignee_filter: string;
  due_window: string;
  overdue: string;
  color: string;
  statuses: string;
  work_types: string;
  approval_states: string;
  priority_min: string;
  priority_max: string;
  labels: string;
  due_set: string;
  release_assigned: string;
  component_assigned: string;
  blocked: string;
  development_providers: string;
  development_event_types: string;
  development_states: string;
  comment_contains: string;
  attachment_media_types: string;
  link_types: string;
  changed_fields: string;
  sprint_scope_action: string;
};
