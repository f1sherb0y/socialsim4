import axios from "axios";

import { useAuthStore } from "../store/auth";

export const API_BASE_URL = (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined) ?? "http://localhost:8000/api";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
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
