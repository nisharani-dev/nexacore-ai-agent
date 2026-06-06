// main.jsx — Vite entry point
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";
import Callback from "./Callback";

const Root = window.location.pathname === "/callback" ? Callback : App;

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <Root />
  </StrictMode>
);
