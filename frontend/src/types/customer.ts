export interface CustomerProfile {
  id: number;
  external_customer_id: string;
  name: string;
  email: string;
  lifetime_value: number;
  successful_payments: number;
  failed_payments: number;
  opted_out: boolean;
}

export interface CustomerSummary {
  total_transactions: number;
  successful_payments: number;
  failed_payments: number;
  open_recovery_cases: number;
  recovered_cases: number;
  amount_at_risk: number;
  recovery_rate: number;
}

export interface CustomerTransaction {
  id: number;
  external_transaction_id: string;
  amount: number;
  currency: string;
  status: string;
  failure_reason: string | null;
  payment_method: string | null;
  razorpay_payment_id: string | null;
  razorpay_order_id: string | null;
  created_at: string;
}

export interface CustomerRecoveryCase {
  id: number;
  transaction_id: number;
  amount_at_risk: number;
  failure_class: string;
  status: string;
  attempt_count: number;
  next_action_at: string | null;
  created_at: string;
  resolved_at: string | null;
}