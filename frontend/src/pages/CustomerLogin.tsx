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

  const [customerAccessId, setCustomerAccessId] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();

    setError("");

    const accessId = customerAccessId
      .trim()
      .toUpperCase();

    if (!accessId) {
      setError("Please enter your Customer Access ID.");
      return;
    }

    try {
      setLoading(true);

      const response = await customerLogin(accessId);


      /*
       * Make sure the returned account is actually
       * a customer account.
       */
      if (response.user.role !== "CUSTOMER") {
        setError(
          "This account is not a customer account.",
        );

        return;
      }


      /*
       * Make sure the authenticated user is linked
       * to a valid customer profile.
       */
      if (
        !response.user.customer_id ||
        response.user.customer_id <= 0
      ) {
        setError(
          "Customer account is not properly configured.",
        );

        return;
      }


      /*
       * Store authentication information only after
       * successful verification.
       */
      sessionStorage.setItem(
        "razorrecover_access_token",
        response.access_token,
      );


      sessionStorage.setItem(
        "razorrecover_user",
        JSON.stringify(response.user),
      );


      /*
       * Redirect to the customer dashboard.
       */
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
            Enter your Customer Access ID to view your
            payments, recovery status, and
            available recovery offers.
          </p>

        </div>


        {/* Customer Access Form */}
        <form
          className="auth-form"
          onSubmit={handleSubmit}
        >

          <label htmlFor="customer-access-id">
            Customer Access ID
          </label>

          <input
            id="customer-access-id"
            type="text"
            inputMode="text"
            placeholder="CUST-ZN7N8J"
            autoComplete="off"
            value={customerAccessId}
            onChange={(event) =>
              setCustomerAccessId(event.target.value)
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