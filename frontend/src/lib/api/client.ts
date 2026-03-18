// ============================================================
// Axios API Client — Base instance with auth + error handling
// ============================================================

import axios from "axios";
import { getToken, removeToken } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const apiClient = axios.create({
    baseURL: API_URL,
    timeout: 30000,
    headers: {
        "Content-Type": "application/json",
    },
});

// Request interceptor — inject JWT token
apiClient.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Response interceptor — handle errors + auto-logout on 401
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response) {
            const { status, data } = error.response;
            const message = data?.detail || data?.message || "An error occurred";
            console.error(`[API Error] ${status}: ${message}`);

            // Token expired or invalid — clear and redirect to login
            if (status === 401 && typeof window !== "undefined") {
                removeToken();
                window.location.href = "/login";
            }

            // Rate limited
            if (status === 429) {
                console.warn("[API] Rate limit exceeded — slow down requests");
            }
        } else if (error.request) {
            console.error("[API Error] No response from server");
        }
        return Promise.reject(error);
    }
);

export default apiClient;
