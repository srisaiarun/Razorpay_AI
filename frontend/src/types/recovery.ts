
export type RecoveryStatus =
  | "OPEN"
  | "RECOVERED"
  | "CLOSED";

export type PriorityBand =
  | "P1_HIGH"
  | "P2"
  | "P3"
  | "P4";

export type RecoveryRiskBand =
  | "HIGH"
  | "MEDIUM"
  | "LOW";

export type RecoveryActionType =
  | "HIGH_PRIORITY_RECOVERY"
  | "STANDARD_RECOVERY"
  | "LOW_COST_RECOVERY"
  | "MONITOR"
  | "NO_ACTION";

export type RecoveryActionStatus =
  | "PENDING_APPROVAL"
  | "PENDING"
  | "COMPLETED"
  | "FAILED"
  | "SKIPPED";


export interface RecoveryCase {
  id: number;
  transaction_id: number;
  customer_id: number;
  amount_at_risk: number;
  failure_class: string;
  risk_score: number;
  recovery_probability: number | null;
  status: RecoveryStatus;
  attempt_count: number;
  next_action_at: string | null;
  created_at: string;
  resolved_at: string | null;
}


export interface RecoveryQueueItem {
  recovery_case_id: number;
  customer_id: number;
  amount_at_risk: number;
  recovery_probability: number;
  expected_recovery_value: number;
  priority_score: number;
  recovery_risk_band: RecoveryRiskBand;
  priority_band: PriorityBand;
  recommended_action: RecoveryActionType;
  targeted_by_capacity_policy: boolean;
  status: RecoveryStatus;
  attempt_count: number;
  next_action_at: string | null;
}


export interface RecoveryQueueResponse {
  total: number;
  limit: number;
  items: RecoveryQueueItem[];
}


export interface AgentDecision {
  id: number;
  recovery_case_id: number;
  decision: RecoveryActionType;
  reasoning_summary: string;
  confidence: number;
  expected_recovery_amount: number;
  policy_status: string;
  requires_human_approval: boolean;
  created_at: string;
}

export interface AdminDecision {
  id: number;
  recovery_case_id: number;
  customer_id: number;
  decision: string;
  reasoning_summary: string;
  confidence: number;
  expected_recovery_amount: number;
  policy_status: string;
  requires_human_approval: boolean;
  action_id: number | null;
  action_type: string | null;
  action_status: string | null;
  case_status: RecoveryStatus;
  created_at: string;
}


export interface RecoveryAction {
  id: number;
  recovery_case_id: number;
  agent_decision_id: number;
  action_type: RecoveryActionType;
  status: RecoveryActionStatus;
  amount: number;
  external_reference: string | null;
  failure_reason: string | null;
  attempt_number: number;
  created_at: string;
  completed_at: string | null;
}


export interface AuditLog {
  id: number;
  recovery_case_id: number;
  event_type: string;
  actor_type: string;
  actor_id: string;
  message: string;
  event_data: Record<string, unknown>;
  created_at: string;
}


export interface RecoveryDecisionResponse {
  recovery_case_id: number;
  agent_decision_id: number;
  recovery_action_id: number;
  decision: RecoveryActionType;
  reasoning_summary: string;
  confidence: number;
  expected_recovery_amount: number;
  policy_status: string;
  requires_human_approval: boolean;
  action_type: RecoveryActionType;
  action_status: RecoveryActionStatus;
  amount: number;
  created_at: string;
}


export interface ApprovalRequest {
  approver_id: string;
  approval_reason?: string | null;
} 