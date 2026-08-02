import { FileUp, LoaderCircle, Upload } from "lucide-react";
import { useRef, useState } from "react";

type FileUploadPanelProps = {
  busy: boolean;
  disabled: boolean;
  error: string | null;
  onFileChange: () => void;
  onUpload: (file: File) => Promise<boolean>;
};

function supportedFilename(filename: string): boolean {
  return /\.(md|txt|pdf)$/i.test(filename);
}

export default function FileUploadPanel({
  busy,
  disabled,
  error,
  onFileChange,
  onUpload,
}: FileUploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const chooseFile = (nextFile: File | null) => {
    onFileChange();
    if (nextFile !== null && !supportedFilename(nextFile.name)) {
      setFile(null);
      setValidationError("Only .md, .txt, and .pdf files are supported");
      return;
    }
    setFile(nextFile);
    setValidationError(null);
  };

  const submit = async () => {
    if (file === null) {
      setValidationError("Choose a document before uploading");
      return;
    }
    const succeeded = await onUpload(file);
    if (succeeded) {
      setFile(null);
      if (inputRef.current !== null) {
        inputRef.current.value = "";
      }
    }
  };

  const visibleError = validationError ?? error;

  return (
    <section className="document-upload-panel" aria-labelledby="document-upload-heading">
      <header>
        <div>
          <span className="knowledge-eyebrow">Document ingestion</span>
          <h3 id="document-upload-heading">Upload document</h3>
        </div>
        <FileUp size={19} aria-hidden="true" />
      </header>
      <p id="document-upload-help">
        Markdown, text, and text-layer PDF files are processed synchronously.
      </p>
      <form
        aria-label="Upload document"
        aria-busy={busy}
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <label className="document-file-picker">
          <span>Document</span>
          <input
            ref={inputRef}
            type="file"
            accept=".md,.txt,.pdf"
            aria-describedby="document-upload-help"
            disabled={busy || disabled}
            onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <div className="document-file-selection" aria-live="polite">
          {file === null ? (
            <span>No file selected</span>
          ) : (
            <>
              <strong>{file.name}</strong>
              <span>{file.size.toLocaleString()} bytes</span>
            </>
          )}
        </div>
        {visibleError ? (
          <p className="knowledge-form-error" role="alert">
            {visibleError}
          </p>
        ) : null}
        <button type="submit" disabled={busy || disabled || file === null}>
          {busy ? (
            <LoaderCircle size={15} aria-hidden="true" />
          ) : (
            <Upload size={15} aria-hidden="true" />
          )}
          {busy ? "Uploading..." : "Upload"}
        </button>
      </form>
    </section>
  );
}
