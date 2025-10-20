import axios from "axios";

import { useAuthStore } from "../store/auth";

const configuredBackendBaseUrl = import.meta.env.VITE_BACKEND_BASE_URL as string | undefined;
const rawFrontendBaseUrl = import.meta.env.BASE_URL;
const frontendBasePath = rawFrontendBaseUrl === "/" ? "" : rawFrontendBaseUrl.replace(/\/$/, "");
const origin = window.location.origin;
const defaultBackendBaseUrl = `${origin}${frontendBasePath}/api`;

function resolveBackendBaseUrl(candidate: string | undefined): string {
  const trimmed = candidate?.trim();
  if (!trimmed) {
    return defaultBackendBaseUrl;
  }
  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }
  if (trimmed.startsWith("/")) {
    return `${origin}${trimmed}`;
  }
  if (frontendBasePath) {
    return `${origin}${frontendBasePath}/${trimmed}`;
  }
  return `${origin}/${trimmed}`;
}

export const API_BASE_URL = resolveBackendBaseUrl(configuredBackendBaseUrl).replace(/\/+$/, "");
console.log("Api base url is :", API_BASE_URL);

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/`,
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { response, config } = error;
    if (response?.status === 401 && !config.__isRetryRequest) {
      const refreshToken = useAuthStore.getState().refreshToken;
      if (refreshToken) {
        try {
          const refreshResponse = await axios.post(
            `${API_BASE_URL.replace(/\/$/, "")}/auth/token/refresh`,
            { refresh_token: refreshToken },
          );
          const data = refreshResponse.data as {
            access_token: string;
            refresh_token: string;
          };
          useAuthStore.getState().updateTokens(data.access_token, data.refresh_token);
          config.__isRetryRequest = true;
          config.headers.Authorization = `Bearer ${data.access_token}`;
          return apiClient(config);
        } catch (refreshError) {
          useAuthStore.getState().clearSession();
        }
      }
    }
    return Promise.reject(error);
  },
);
