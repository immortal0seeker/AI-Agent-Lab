import { getJson } from "./client";
import type { ModelOption } from "../types/models";

export function fetchModels(): Promise<ModelOption[]> {
  return getJson<ModelOption[]>("/models");
}
