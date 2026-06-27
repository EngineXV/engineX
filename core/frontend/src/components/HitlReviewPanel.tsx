interface HitlEvidence {
  id: string;
  label: string;
  kind: string;
  content: string;
}

interface HitlAuditCard {
  node_id?: string;
  node_name?: string;
  reviewed_at?: string;
  prompt?: string;
  evidence_count?: number;
  attachment_count?: number;
  attachments?: Array<{ name: string; path: string }>;
}

interface HitlReviewPanelProps {
  visible: boolean;
  prompt?: string;
  evidence?: HitlEvidence[];
  auditCard?: HitlAuditCard;
  onApprove: () => void;
  onReject: () => void;
}

export default function HitlReviewPanel({
  visible,
  prompt,
  evidence = [],
  auditCard,
  onApprove,
  onReject,
}: HitlReviewPanelProps) {
  if (!visible) return null;

  return (
    <div className="hitl-review-panel" role="region" aria-label="Human review">
      <div className="hitl-review-header">
        <strong>Human review required</strong>
        {auditCard?.node_name ? (
          <span className="hitl-review-node">{auditCard.node_name}</span>
        ) : null}
      </div>
      <p className="hitl-review-prompt">
        {prompt || "The agent paused for your decision. Reply in chat to approve, edit, or reject."}
      </p>

      {auditCard ? (
        <div className="hitl-audit-card">
          <div className="hitl-audit-row">
            <span>Evidence items</span>
            <strong>{auditCard.evidence_count ?? evidence.length}</strong>
          </div>
          {auditCard.attachments && auditCard.attachments.length > 0 ? (
            <div className="hitl-attachments">
              <strong>Attachments</strong>
              <ul>
                {auditCard.attachments.map((item) => (
                  <li key={item.name}>
                    <span>{item.name}</span>
                    <code>{item.path}</code>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      {evidence.length > 0 ? (
        <div className="hitl-evidence-list">
          {evidence.map((item) => (
            <article key={item.id} className={`hitl-evidence-card hitl-evidence-${item.kind}`}>
              <header>{item.label}</header>
              <pre>{item.content}</pre>
            </article>
          ))}
        </div>
      ) : null}

      <div className="hitl-review-actions">
        <button type="button" className="btn-secondary" onClick={onReject}>
          Needs changes
        </button>
        <button type="button" className="btn-primary" onClick={onApprove}>
          Approve & continue
        </button>
      </div>
    </div>
  );
}

export type { HitlEvidence, HitlAuditCard };
