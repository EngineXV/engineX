import { useCallback, useEffect, useMemo, useState } from "react";
import { credentialsApi, type CredentialSpec } from "../api/integrations";
import { IconExternal, IconKey } from "../components/Icons";

export default function CredentialsPage() {
  const [specs, setSpecs] = useState<CredentialSpec[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [editor, setEditor] = useState<CredentialSpec | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await credentialsApi.listSpecs();
      setSpecs(data.specs);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load credentials");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return specs;
    return specs.filter(
      (s) =>
        s.credential_name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.env_var.toLowerCase().includes(q),
    );
  }, [specs, search]);

  const openEditor = (spec: CredentialSpec) => {
    setEditor(spec);
    setApiKey("");
    setValidation(null);
  };

  const validate = async () => {
    if (!editor || !apiKey.trim()) return;
    setValidating(true);
    try {
      const result = await credentialsApi.validateKey(editor.credential_id, apiKey.trim());
      setValidation(
        result.valid === true
          ? "Key looks valid."
          : result.valid === false
            ? result.message || "Key validation failed."
            : result.message || "Could not validate key.",
      );
    } catch (e) {
      setValidation(e instanceof Error ? e.message : "Validation failed");
    } finally {
      setValidating(false);
    }
  };

  const save = async () => {
    if (!editor || !apiKey.trim()) return;
    setSaving(true);
    try {
      await credentialsApi.save(editor.credential_id, {
        [editor.credential_key || "api_key"]: apiKey.trim(),
      });
      setEditor(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save credential");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (spec: CredentialSpec) => {
    if (!window.confirm(`Remove credential for ${spec.credential_name}?`)) return;
    try {
      await credentialsApi.delete(spec.credential_id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete credential");
    }
  };

  return (
    <div className="feature-page">
      <header className="feature-header">
        <div>
          <h1>Credentials</h1>
          <p>Manage API keys and integrations used by your agents.</p>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="feature-toolbar">
        <input
          className="search-input"
          placeholder="Search credentials…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <p className="muted">Loading credentials…</p>
      ) : (
        <div className="cred-grid">
          {filtered.map((spec) => (
            <article key={spec.credential_id} className="cred-card">
              <div className="cred-card-top">
                <span className="cred-icon"><IconKey size={18} /></span>
                <div>
                  <h2>{spec.credential_name}</h2>
                  <p>{spec.description}</p>
                </div>
                <span className={`status-chip ${spec.available ? "ok" : "missing"}`}>
                  {spec.available ? "Connected" : "Not set"}
                </span>
              </div>
              <div className="cred-meta">{spec.env_var}</div>
              <div className="cred-actions">
                {spec.direct_api_key_supported && (
                  <button type="button" className="btn-secondary" onClick={() => openEditor(spec)}>
                    {spec.available ? "Update" : "Add key"}
                  </button>
                )}
                {spec.available && (
                  <button type="button" className="btn-ghost" onClick={() => void remove(spec)}>
                    Remove
                  </button>
                )}
                {spec.help_url && (
                  <a className="btn-link" href={spec.help_url} target="_blank" rel="noreferrer">
                    Docs <IconExternal />
                  </a>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {editor && (
        <div className="modal-backdrop" onClick={() => setEditor(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{editor.credential_name}</h2>
            <p className="muted">{editor.api_key_instructions || editor.description}</p>
            <label className="field-label">{editor.env_var}</label>
            <input
              type="password"
              className="text-input"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Paste API key"
            />
            {validation && <p className="validation-msg">{validation}</p>}
            <div className="modal-actions">
              <button type="button" className="btn-ghost" onClick={() => setEditor(null)}>
                Cancel
              </button>
              <button
                type="button"
                className="btn-secondary"
                disabled={validating || !apiKey.trim()}
                onClick={() => void validate()}
              >
                {validating ? "Checking…" : "Validate"}
              </button>
              <button
                type="button"
                className="primary"
                disabled={saving || !apiKey.trim()}
                onClick={() => void save()}
              >
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
