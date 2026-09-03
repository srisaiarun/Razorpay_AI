import type {
  AdminCustomer,
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

// -----------------------------------------------------------------------------
// Authentication Types
// -----------------------------------------------------------------------------

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  role: "CUSTOMER" | "MANAGEMENT";
  status: string;
  customer_id: number | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}


// -----------------------------------------------------------------------------
// Generic API Request
// -----------------------------------------------------------------------------

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const token = sessionStorage.getItem(
    "razorrecover_access_token",
  );

  const response = await fetch(
    `${API_BASE_URL}${path}`,
    {
      ...options,
      headers: {
        "Content-Type": "application/json",

        ...(token
          ? {
              Authorization: `Bearer ${token}`,
            }
          : {}),

        ...(options?.headers ?? {}),
      },
    },
  );

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const errorData = await response.json();

      if (
        typeof errorData?.detail === "string"
      ) {
        message = errorData.detail;
      }
    } catch {
      // Ignore JSON parsing errors.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}


// -----------------------------------------------------------------------------
// Authentication
// -----------------------------------------------------------------------------

export async function login(
  email: string,
  password: string,
): Promise<AuthResponse> {
  return request<AuthResponse>(
    "/api/v1/auth/login",
    {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
      }),
    },
  );
}


export async function getCurrentUser(): Promise<AuthUser> {
  return request<AuthUser>(
    "/api/v1/auth/me",
  );
}


export function logout(): void {
  sessionStorage.removeItem(
    "razorrecover_access_token",
  );

  sessionStorage.removeItem(
    "razorrecover_user",
  );
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

export async function getAllDecisions(): Promise<
  AdminDecision[]
> {
  return request<AdminDecision[]>(
    "/api/v1/recovery-cases/decisions",
  );
}


// -----------------------------------------------------------------------------
// Admin — Customers
// -----------------------------------------------------------------------------

export async function getAllCustomers(): Promise<
  AdminCustomer[]
> {
  return request<AdminCustomer[]>(
    "/api/v1/recovery-cases/customers",
  );
}


// -----------------------------------------------------------------------------
// Admin — Recovery Actions
// -----------------------------------------------------------------------------

export async function getAllRecoveryActions(): Promise<
  RecoveryAction[]
> {
  return request<RecoveryAction[]>(
    "/api/v1/recovery-actions",
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


// -----------------------------------------------------------------------------
// Agent Decision Type
// -----------------------------------------------------------------------------
//
// Prevent unused-import errors if the API contract expands later.

export type {
  AgentDecision,
};