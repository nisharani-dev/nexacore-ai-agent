import { useEffect, useState } from "react";
import { completeOidcLogin } from "./api";

export default function Callback() {
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");
    if (!code) {
      setError("Missing authorization code.");
      return;
    }

    completeOidcLogin(code, state)
      .then((result) => {
        if (result.id_token) {
          localStorage.setItem("oidc_id_token", result.id_token);
        }
        if (result.access_token) {
          localStorage.setItem("oidc_access_token", result.access_token);
        }
        if (result.user_info?.email) {
          localStorage.setItem("oidc_user_email", result.user_info.email);
        }
        setDone(true);
        window.location.replace("/");
      })
      .catch((err) => setError(err.message || "OIDC callback failed"));
  }, []);

  return (
    <div className="ob-overlay">
      <div className="ob-card">
        <div className="ob-logo"><span className="ob-dot" />RAMP</div>
        {error ? (
          <p className="ob-sub">{error}</p>
        ) : (
          <p className="ob-sub">{done ? "Redirecting…" : "Completing sign-in…"}</p>
        )}
      </div>
    </div>
  );
}
