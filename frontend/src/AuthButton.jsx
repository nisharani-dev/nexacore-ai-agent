import { useEffect, useState } from "react";
import { getOidcInfo, startOidcLogin } from "./api";

export default function AuthButton() {
  const [info, setInfo] = useState(null);

  useEffect(() => {
    getOidcInfo().then(setInfo).catch(() => setInfo({ enabled: false }));
  }, []);

  if (!info?.enabled) {
    return (
      <span className="auth-pill auth-pill--off" title="Set OIDC_PROVIDER to enable SSO">
        SSO off
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
