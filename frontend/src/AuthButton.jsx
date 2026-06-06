import { useEffect, useState } from "react";
import { getOidcInfo, startOidcLogin } from "./api";

export default function AuthButton() {
  const [info, setInfo] = useState(null);
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    getOidcInfo().then(setInfo).catch(() => setInfo({ enabled: false }));
    setSignedIn(Boolean(localStorage.getItem("oidc_id_token") || localStorage.getItem("oidc_access_token")));
  }, []);

  if (!info?.enabled) {
    return (
      <span className="auth-pill auth-pill--off" title="Set OIDC_PROVIDER to enable SSO">
        SSO off
      </span>
    );
  }

  if (signedIn) {
    const email = localStorage.getItem("oidc_user_email");
    return (
      <span className="auth-pill auth-pill--on" title={email || "Signed in"}>
        {email ? email.split("@")[0] : "signed in"}
      </span>
    );
  }

  return (
    <button
      className="auth-pill auth-pill--on"
      onClick={() => startOidcLogin()}
      type="button"
    >
      Sign in · {info.provider}
    </button>
  );
}
