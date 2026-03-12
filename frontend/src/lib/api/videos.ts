import apiClient from "./client";
import { Video, VideoFilters, URLSubmitRequest, SubmitResponse } from "./types";

export async function submitUrl(data: URLSubmitRequest): Promise<SubmitResponse> {
    const res = await apiClient.post<SubmitResponse>("/videos/from-url", data);
    return res.data;
}

export async function listVideos(filters?: VideoFilters): Promise<Video[]> {
    const res = await apiClient.get<Video[]>("/videos/", { params: filters });
    return res.data;
}

export async function getVideo(id: string): Promise<Video> {
    const res = await apiClient.get<Video>(`/videos/${id}`);
    return res.data;
}

export async function deleteVideo(id: string): Promise<void> {
    await apiClient.delete(`/videos/${id}`);
}
