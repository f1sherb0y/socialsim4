import { ReactNode, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuthStore } from "../store/auth";

type Props = {
  children: ReactNode;
};

export function RequireAuth({ children }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const checkSession = useAuthStore((state) => state.restoreSession);

  useEffect(() => {
    checkSession();
  }, [checkSession]);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login", { replace: true, state: { from: location } });
    }
  }, [isAuthenticated, navigate, location]);

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
