import type {
  AdminDecision,
  AgentDecision,
  ApprovalRequest,
  AuditLog,
  RecoveryAction,
  RecoveryCase,
  RecoveryDecisionResponse,
  RecoveryQueueResponse,
} from "../types/recovery";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000";


async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(
    `${API_BASE_URL}${path}`,
    {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers ?? {}),
      },
    },
  );

  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`;

    try {
      const body = await response.json();

      if (typeof body?.detail === "string") {
        message = body.detail;
      }
    } catch {
      // Keep the default error message.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}


// -----------------------------------------------------------------------------
// Recovery Cases
// -----------------------------------------------------------------------------

export async function getRecoveryQueue(
  limit = 50,
): Promise<RecoveryQueueResponse> {
  return request<RecoveryQueueResponse>(
    `/api/v1/recovery-cases/queue?limit=${limit}`,
  );
}


export async function getRecoveryCase(
  recoveryCaseId: number,
): Promise<RecoveryCase> {
  return request<RecoveryCase>(
    `/api/v1/recovery-cases/${recoveryCaseId}`,
  );
}


export async function getRecoveryDecision(
  recoveryCaseId: number,
): Promise<RecoveryDecisionResponse> {
  return request<RecoveryDecisionResponse>(
    `/api/v1/recovery-cases/${recoveryCaseId}/decision`,
  );
}


export async function getRecoveryActions(
  recoveryCaseId: number,
): Promise<RecoveryAction[]> {
  return request<RecoveryAction[]>(
    `/api/v1/recovery-cases/${recoveryCaseId}/actions`,
  );
}


export async function getRecoveryAudit(
  recoveryCaseId: number,
): Promise<AuditLog[]> {
  return request<AuditLog[]>(
    `/api/v1/recovery-cases/${recoveryCaseId}/audit`,
  );
}


// -----------------------------------------------------------------------------
// Decision
// -----------------------------------------------------------------------------

export async function createRecoveryDecision(
  recoveryCaseId: number,
): Promise<RecoveryDecisionResponse> {
  return request<RecoveryDecisionResponse>(
    `/api/v1/recovery-cases/${recoveryCaseId}/decide`,
    {
      method: "POST",
    },
  );
}


// -----------------------------------------------------------------------------
// Recovery Actions
// -----------------------------------------------------------------------------

export async function approveRecoveryAction(
  actionId: number,
  approval: ApprovalRequest,
): Promise<RecoveryAction> {
  return request<RecoveryAction>(
    `/api/v1/recovery-actions/${actionId}/approve`,
    {
      method: "POST",
      body: JSON.stringify(approval),
    },
  );
}


export async function executeRecoveryAction(
  actionId: number,
): Promise<RecoveryAction> {
  return request<RecoveryAction>(
    `/api/v1/recovery-actions/${actionId}/execute`,
    {
      method: "POST",
    },
  );
}
// -----------------------------------------------------------------------------
// Admin — Decisions
// -----------------------------------------------------------------------------

export async function getAllDecisions(): Promise<AdminDecision[]> {
  return request<AdminDecision[]>(
    "/api/v1/recovery-cases/decisions",
  );
}

// -----------------------------------------------------------------------------
// Health
// -----------------------------------------------------------------------------

export async function getHealth(): Promise<{
  status: string;
  service: string;
  version: string;
}> {
  return request<{
    status: string;
    service: string;
    version: string;
  }>("/health");
}


// Prevent unused-import errors if the API contract expands later.
export type {
  AgentDecision,
};