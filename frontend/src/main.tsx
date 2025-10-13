import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import "./styles.css";
import "./i18n";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
    },
  },
});

const root = document.getElementById("root") as HTMLElement;
const tree = (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </QueryClientProvider>
);

// Avoid StrictMode double-invocation in development so effects (e.g., requests) run only once.
ReactDOM.createRoot(root).render(import.meta.env.PROD ? <React.StrictMode>{tree}</React.StrictMode> : tree);
