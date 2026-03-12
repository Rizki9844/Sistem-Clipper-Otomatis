import apiClient from "./client";
import { Clip, ClipFilters } from "./types";

export async function listClips(filters?: ClipFilters): Promise<Clip[]> {
    const res = await apiClient.get<Clip[]>("/clips/", { params: filters });
    return res.data;
}

export async function getClip(id: string): Promise<Clip> {
    const res = await apiClient.get<Clip>(`/clips/${id}`);
    return res.data;
}

export async function reviewClip(
    id: string,
    action: "approve" | "reject",
    notes?: string
): Promise<{ message: string }> {
    const res = await apiClient.post(`/clips/${id}/review`, null, {
        params: { action, notes },
    });
    return res.data;
}

export async function batchReview(
    clipIds: string[],
    action: "approve" | "reject"
): Promise<{ message: string; updated: number }> {
    const res = await apiClient.post(`/clips/batch-review`, clipIds, {
        params: { action },
    });
    return res.data;
}

export async function getDownloadUrl(
    id: string,
    expiryHours: number = 4
): Promise<{ download_url: string }> {
    const res = await apiClient.get(`/clips/${id}/download-url`, {
        params: { expiry_hours: expiryHours },
    });
    return res.data;
}
