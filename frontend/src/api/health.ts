import { getJson } from "./client";

export type HealthResponse = {
  status: string;
  service: string;
};

export function fetchHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}
