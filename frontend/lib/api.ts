import { createClient } from "@/lib/supabase/client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL!;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    
    let errorMessage = "Terjadi kesalahan tak terduga.";
    if (body?.detail) {
      errorMessage = typeof body.detail === 'string' 
        ? body.detail 
        : Array.isArray(body.detail) 
          ? body.detail.map((e: any) => e.msg).join(', ') 
          : JSON.stringify(body.detail);
    } else if (body?.error?.message) {
      errorMessage = body.error.message;
    }

    throw new ApiError(response.status, errorMessage);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json();
}

async function postFormData<T>(path: string, formData: FormData): Promise<T> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    
    let errorMessage = "Terjadi kesalahan tak terduga.";
    if (body?.detail) {
      errorMessage = typeof body.detail === 'string' 
        ? body.detail 
        : Array.isArray(body.detail) 
          ? body.detail.map((e: any) => e.msg).join(', ') 
          : JSON.stringify(body.detail);
    } else if (body?.error?.message) {
      errorMessage = body.error.message;
    }

    throw new ApiError(response.status, errorMessage);
  }
  return response.json();
}

async function downloadFile(path: string): Promise<{ blob: Blob; filename: string }> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.error?.message ?? "Gagal mengunduh file.");
  }

  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filename = disposition.match(/filename=(.+)$/)?.[1]?.trim() ?? "rekap-order.xlsx";
  const blob = await response.blob();
  return { blob, filename };
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  postFormData,
  downloadFile,
};
