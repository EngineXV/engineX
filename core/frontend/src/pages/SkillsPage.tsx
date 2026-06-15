import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { skillsApi, type SkillDetail, type SkillRow } from "../api/integrations";

export default function SkillsPage() {
  const [skills, setSkills] = useState<SkillRow[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<SkillDetail | null>(null);
  const [uploadName, setUploadName] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await skillsApi.list();
      setSkills(data.skills);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load skills");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return skills;
    return skills.filter(
      (s) => s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q),
    );
  }, [skills, search]);

  const openSkill = async (name: string) => {
    try {
      const detail = await skillsApi.get(name);
      setSelected(detail);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load skill");
    }
  };

  const onUpload = async (file: File) => {
    try {
      await skillsApi.upload(file, uploadName.trim() || undefined);
      setUploadName("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    }
  };

  const onDelete = async (name: string) => {
    if (!window.confirm(`Delete skill "${name}"?`)) return;
    try {
      await skillsApi.delete(name);
      if (selected?.name === name) setSelected(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  return (
    <div className="feature-page skills-page">
      <header className="feature-header">
        <div>
          <h1>Skills</h1>
          <p>Reusable instruction packs agents can draw on at runtime.</p>
        </div>
        <div className="feature-header-actions">
          <input
            className="text-input compact"
            placeholder="Name (for .md upload)"
            value={uploadName}
            onChange={(e) => setUploadName(e.target.value)}
          />
          <input
            ref={fileRef}
            type="file"
            accept=".md,.zip"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void onUpload(file);
              e.target.value = "";
            }}
          />
          <button type="button" className="primary" onClick={() => fileRef.current?.click()}>
            Upload skill
          </button>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="feature-toolbar">
        <input
          className="search-input"
          placeholder="Search skills…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="skills-layout">
        <section className="skills-list panel">
          {loading ? (
            <p className="muted pad">Loading…</p>
          ) : filtered.length === 0 ? (
            <p className="muted pad">
              No skills yet. Upload a SKILL.md or zip to <code>~/.engine/skills/</code>.
            </p>
          ) : (
            filtered.map((skill) => (
              <button
                key={skill.name}
                type="button"
                className={`skill-row${selected?.name === skill.name ? " active" : ""}`}
                onClick={() => void openSkill(skill.name)}
              >
                <strong>{skill.name}</strong>
                <span>{skill.description || "No description"}</span>
                <span className="skill-scope">{skill.scope}</span>
              </button>
            ))
          )}
        </section>

        <section className="skills-detail panel">
          {!selected ? (
            <p className="muted pad">Select a skill to view its contents.</p>
          ) : (
            <>
              <div className="skills-detail-header">
                <div>
                  <h2>{selected.name}</h2>
                  <p className="muted">{selected.description}</p>
                </div>
                {selected.scope === "user" && (
                  <button type="button" className="btn-ghost danger" onClick={() => void onDelete(selected.name)}>
                    Delete
                  </button>
                )}
              </div>
              <pre className="skill-body">{selected.body}</pre>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
