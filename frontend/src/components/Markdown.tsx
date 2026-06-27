import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Renderiza o relatório (markdown com tabelas GFM). Links minio:// NÃO navegam — viram
// um chip de código (a fonte é inspecionável pelo painel de Fontes, não pelo browser).
export function Markdown({ children }: { children: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children }) {
            if (href && href.startsWith("minio://")) {
              return <code className="fonte-inline">{children}</code>;
            }
            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
