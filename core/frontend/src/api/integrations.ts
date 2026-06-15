export interface CredentialSpec {
  credential_name: string;
  credential_id: string;
  env_var: string;
  description: string;
  help_url: string;
  api_key_instructions: string;
  tools: string[];
  direct_api_key_supported: boolean;
  engine_oauth_supported: boolean;
  credential_key: string;
  credential_group: string;
  available: boolean;
}

export interface SkillRow {
  name: string;
  description: string;
  scope: string;
  path: string;
  enabled: boolean;
  provenance: string;
}

export interface SkillDetail extends SkillRow {
  body: string;
  files: string[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = (body as { error?: string }).error || res.statusText;
    throw new Error(message);
  }
  return body as T;
}

export const credentialsApi = {
  listSpecs: () => request<{ specs: CredentialSpec[] }>("/credentials/specs"),
  save: (credentialId: string, keys: Record<string, string>) =>
    request<{ saved: string }>("/credentials", {
      method: "POST",
      body: JSON.stringify({ credential_id: credentialId, keys }),
    }),
  delete: (credentialId: string) =>
    request<{ deleted: boolean }>(`/credentials/${credentialId}`, { method: "DELETE" }),
  validateKey: (providerId: string, apiKey: string) =>
    request<{ valid: boolean | null; message: string }>("/credentials/validate-key", {
      method: "POST",
      body: JSON.stringify({ provider_id: providerId, api_key: apiKey }),
    }),
};

export const skillsApi = {
  list: () => request<{ skills: SkillRow[]; count: number }>("/skills"),
  get: (name: string) => request<SkillDetail>(`/skills/${encodeURIComponent(name)}`),
  delete: (name: string) =>
    request<{ deleted: boolean }>(`/skills/${encodeURIComponent(name)}`, { method: "DELETE" }),
  upload: async (file: File, name?: string) => {
    const form = new FormData();
    form.append("file", file);
    const qs = name ? `?name=${encodeURIComponent(name)}` : "";
    const res = await fetch(`/api/skills/upload${qs}`, { method: "POST", body: form });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error((body as { error?: string }).error || res.statusText);
    return body as { uploaded: string };
  },
};
