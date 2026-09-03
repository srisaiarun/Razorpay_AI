import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  LockKeyhole,
  ShieldCheck,
} from "lucide-react";

import { useState } from "react";
import type { FormEvent } from "react";

import { Link, useNavigate } from "react-router-dom";

import { customerLogin } from "../services/api";


export default function CustomerLogin() {
  const navigate = useNavigate();

  const [customerId, setCustomerId] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    setError("");

    const trimmedCustomerId = customerId.trim();

    if (!trimmedCustomerId) {
      setError("Please enter your Customer ID.");
      return;
    }

    const parsedCustomerId = Number(trimmedCustomerId);

    if (
      !Number.isInteger(parsedCustomerId) ||
      parsedCustomerId <= 0
    ) {
      setError("Please enter a valid Customer ID.");
      return;
    }


    try {
      setLoading(true);

      const response = await customerLogin(
        parsedCustomerId,
      );


      if (response.user.role !== "CUSTOMER") {
        setError(
          "This account is not a customer account.",
        );

        return;
      }


      if (response.user.customer_id !== parsedCustomerId) {
        setError(
          "Customer authentication could not be verified.",
        );

        return;
      }


      sessionStorage.setItem(
        "razorrecover_access_token",
        response.access_token,
      );


      sessionStorage.setItem(
        "razorrecover_user",
        JSON.stringify(response.user),
      );


      navigate("/customer/dashboard", {
        replace: true,
      });

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to access the customer portal.",
      );
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="auth-page">

      <div className="auth-card">

        {/* Back */}
        <Link to="/" className="auth-back">
          <ArrowLeft size={16} />
          Back to RazorRecover
        </Link>


        {/* Logo */}
        <div className="auth-logo">

          <div className="landing-brand-mark">
            R
          </div>

          <strong>
            RazorRecover AI
          </strong>

        </div>


        {/* Heading */}
        <div className="auth-heading">

          <div className="landing-eyebrow">
            CUSTOMER PORTAL
          </div>

          <h1>
            Welcome back
          </h1>

          <p>
            Enter your Customer ID to view your
            payments, recovery status, and
            available recovery offers.
          </p>

        </div>


        {/* Customer Access Form */}
        <form
          className="auth-form"
          onSubmit={handleSubmit}
        >

          <label htmlFor="customer-id">
            Customer ID
          </label>

          <input
            id="customer-id"
            type="text"
            inputMode="numeric"
            placeholder="Enter your Customer ID"
            autoComplete="off"
            value={customerId}
            onChange={(event) =>
              setCustomerId(event.target.value)
            }
            disabled={loading}
          />


          {/* Error */}
          {error && (
            <div
              className="auth-error"
              role="alert"
            >
              <AlertCircle size={16} />

              <span>
                {error}
              </span>
            </div>
          )}


          {/* Submit */}
          <button
            type="submit"
            className="landing-primary-button auth-submit"
            disabled={loading}
          >

            {loading ? (
              "Verifying..."
            ) : (
              <>
                Continue
                <ArrowRight size={18} />
              </>
            )}

          </button>

        </form>


        {/* Security */}
        <div className="auth-security">

          <ShieldCheck size={17} />

          <span>
            Secure customer access
          </span>

        </div>


        {/* Management Login */}
        <div className="auth-switch">

          <span>
            Managing recovery operations?
          </span>

          <Link to="/management/login">
            Management Sign In
          </Link>

        </div>

      </div>


      {/* Right Side */}
      <div className="auth-side">

        <LockKeyhole size={32} />

        <h2>
          Your payments.
          <br />
          Your recovery.
        </h2>

        <p>
          Access your payment history and
          recovery activity through your
          personalized customer experience.
        </p>

      </div>

    </div>
  );
}