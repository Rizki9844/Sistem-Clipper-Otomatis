import apiClient from "./client";
import { Job, JobFilters, DashboardStats } from "./types";

export async function listJobs(filters?: JobFilters): Promise<Job[]> {
    const res = await apiClient.get<Job[]>("/jobs/", { params: filters });
    return res.data;
}

export async function getJob(id: string): Promise<Job> {
    const res = await apiClient.get<Job>(`/jobs/${id}`);
    return res.data;
}

export async function cancelJob(id: string): Promise<{ message: string }> {
    const res = await apiClient.post(`/jobs/${id}/cancel`);
    return res.data;
}

export async function retryJob(id: string): Promise<{ message: string }> {
    const res = await apiClient.post(`/jobs/${id}/retry`);
    return res.data;
}

export async function getDashboardStats(): Promise<DashboardStats> {
    const res = await apiClient.get<DashboardStats>("/jobs/stats/dashboard");
    return res.data;
}
