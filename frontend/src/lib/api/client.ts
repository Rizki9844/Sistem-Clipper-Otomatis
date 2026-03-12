// ============================================================
// Axios API Client — Base instance with error handling
// ============================================================

import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const apiClient = axios.create({
    baseURL: API_URL,
    timeout: 30000,
    headers: {
        "Content-Type": "application/json",
    },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response) {
            const data = error.response.data;
            const message = data?.detail || data?.message || "An error occurred";
            console.error(`[API Error] ${error.response.status}: ${message}`);
        } else if (error.request) {
            console.error("[API Error] No response from server");
        }
        return Promise.reject(error);
    }
);

export default apiClient;
