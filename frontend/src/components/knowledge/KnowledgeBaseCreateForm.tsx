import { LoaderCircle, Plus } from "lucide-react";

type KnowledgeBaseCreateFormProps = {
  name: string;
  description: string;
  busy: boolean;
  disabled: boolean;
  error: string | null;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onSubmit: () => void;
};

export default function KnowledgeBaseCreateForm({
  name,
  description,
  busy,
  disabled,
  error,
  onNameChange,
  onDescriptionChange,
  onSubmit,
}: KnowledgeBaseCreateFormProps) {
  return (
    <form
      className="knowledge-create-form"
      aria-label="Create Knowledge Base"
      aria-busy={busy}
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="knowledge-form-heading">
        <span className="knowledge-eyebrow">New collection</span>
        <h2>Create Knowledge Base</h2>
      </div>
      <label>
        <span>Name</span>
        <input
          name="name"
          value={name}
          maxLength={255}
          required
          disabled={busy || disabled}
          onChange={(event) => onNameChange(event.target.value)}
        />
      </label>
      <label>
        <span>Description</span>
        <textarea
          name="description"
          value={description}
          rows={3}
          disabled={busy || disabled}
          onChange={(event) => onDescriptionChange(event.target.value)}
        />
      </label>
      {error ? (
        <p className="knowledge-form-error" role="alert">
          {error}
        </p>
      ) : null}
      <button type="submit" disabled={busy || disabled || !name.trim()}>
        {busy ? (
          <LoaderCircle size={15} aria-hidden="true" />
        ) : (
          <Plus size={15} aria-hidden="true" />
        )}
        {busy ? "Creating..." : "Create"}
      </button>
    </form>
  );
}
