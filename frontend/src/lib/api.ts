// Axios HTTP client plus typed API helpers for auth, orders and assets.
//
// Interceptors:
//  - request: attach the Bearer access token when present.
//  - response: on a 401, try a one-shot refresh using the refresh token and
//    replay the original request; if that fails, clear tokens and redirect to
//    /login.

import axios, {
  AxiosError,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "@/lib/auth";
import type {
  Order,
  OrderDetail,
  ProjectAsset,
  TokenResponse,
  User,
} from "@/types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as
      | (AxiosRequestConfig & { _retry?: boolean })
      | undefined;

    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      getRefreshToken()
    ) {
      original._retry = true;
      try {
        if (!isRefreshing) {
          isRefreshing = true;
          const { data } = await axios.post<TokenResponse>(
            `${API_URL}/auth/refresh`,
            { refresh_token: getRefreshToken() },
          );
          setTokens(data.access_token, data.refresh_token);
          isRefreshing = false;
        }
        const token = getAccessToken();
        if (token && original.headers) {
          original.headers.Authorization = `Bearer ${token}`;
        }
        return api(original);
      } catch (refreshError) {
        isRefreshing = false;
        clearTokens();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);

// ------------------------------- Auth --------------------------------
export const authApi = {
  async register(email: string, password: string, fullName = ""): Promise<TokenResponse> {
    const { data } = await api.post<TokenResponse>("/auth/register", {
      email,
      password,
      full_name: fullName,
    });
    setTokens(data.access_token, data.refresh_token);
    return data;
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    const { data } = await api.post<TokenResponse>("/auth/login", {
      email,
      password,
    });
    setTokens(data.access_token, data.refresh_token);
    return data;
  },

  async me(): Promise<User> {
    const { data } = await api.get<User>("/auth/me");
    return data;
  },
};

// ------------------------------ Orders -------------------------------
export interface OrderCreateInput {
  title: string;
  description?: string;
  category?: string;
  size?: string;
  colors?: string;
  material?: string;
  deadline?: string;
  notes?: string;
}

export const ordersApi = {
  async list(): Promise<Order[]> {
    const { data } = await api.get<Order[]>("/orders");
    return data;
  },

  async get(id: number): Promise<Order> {
    const { data } = await api.get<Order>(`/orders/${id}`);
    return data;
  },

  // Rich detail: order + brief + assets + approvals.
  async getDetail(id: number): Promise<OrderDetail> {
    const { data } = await api.get<OrderDetail>(`/orders/${id}`);
    return data;
  },

  async create(input: OrderCreateInput): Promise<Order> {
    const { data } = await api.post<Order>("/orders", input);
    return data;
  },

  // Phase 2: Claude generates the brief and 6 concept images in one step.
  async generateBrief(id: number): Promise<OrderDetail> {
    const { data } = await api.post<OrderDetail>(`/orders/${id}/generate-brief`);
    return data;
  },

  async generateConcept(id: number): Promise<OrderDetail> {
    const { data } = await api.post<OrderDetail>(`/orders/${id}/generate-concept`);
    return data;
  },

  async approveConcept(
    id: number,
    payload: { approved: boolean; comment?: string },
  ): Promise<OrderDetail> {
    const { data } = await api.post<OrderDetail>(
      `/orders/${id}/approve-concept`,
      payload,
    );
    return data;
  },

  // Phase 3: generate the 3D model (provider + mesh validation) and approve it.
  async generate3D(id: number): Promise<OrderDetail> {
    const { data } = await api.post<OrderDetail>(`/orders/${id}/generate-3d`);
    return data;
  },

  async approveFinal(
    id: number,
    payload: { approved: boolean; comment?: string },
  ): Promise<OrderDetail> {
    const { data } = await api.post<OrderDetail>(
      `/orders/${id}/approve-final`,
      payload,
    );
    return data;
  },
};

// ------------------------------ Assets -------------------------------
export const assetsApi = {
  async list(orderId: number): Promise<ProjectAsset[]> {
    const { data } = await api.get<ProjectAsset[]>(`/orders/${orderId}/assets`);
    return data;
  },

  async upload(orderId: number, file: File): Promise<ProjectAsset> {
    const form = new FormData();
    form.append("file", file);
    const { data } = await api.post<ProjectAsset>(
      `/orders/${orderId}/assets`,
      form,
      { headers: { "Content-Type": "multipart/form-data" } },
    );
    return data;
  },
};
