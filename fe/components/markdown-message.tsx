'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownMessageProps {
  content: string;
  isUser: boolean;
}

export function MarkdownMessage({ content, isUser }: MarkdownMessageProps) {
  if (isUser) {
    // User messages - render as plain text
    return <p className="whitespace-pre-wrap break-words">{content}</p>;
  }

  // Assistant messages - render as markdown
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Headings
          h1: ({ children }) => (
            <h1 className="text-xl font-bold text-foreground mt-4 mb-2 bg-gradient-to-r from-accent-primary to-accent-tertiary bg-clip-text text-transparent">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-semibold text-foreground mt-3 mb-2">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-semibold text-foreground mt-2 mb-1">
              {children}
            </h3>
          ),
          // Paragraphs
          p: ({ children }) => (
            <p className="text-foreground-secondary mb-2 leading-relaxed">
              {children}
            </p>
          ),
          // Lists
          ul: ({ children }) => (
            <ul className="list-disc list-inside space-y-1 mb-2 text-foreground-secondary">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside space-y-1 mb-2 text-foreground-secondary">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="ml-2 text-foreground-secondary">{children}</li>
          ),
          // Code blocks
          code: ({ className, children, ...props }) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code
                  className="bg-background dark:bg-background/60 px-1.5 py-0.5 rounded text-sm font-mono text-accent-tertiary border border-border-light dark:border-border-dark"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <code
                className="block bg-background dark:bg-background/40 p-3 rounded-lg text-sm font-mono overflow-x-auto text-foreground-secondary border border-border-light dark:border-border-dark"
                {...props}
              >
                {children}
              </code>
            );
          },
          pre: ({ children }) => (
            <pre className="bg-background dark:bg-background/40 p-3 rounded-lg mb-2 overflow-x-auto border border-border-light dark:border-border-dark">
              {children}
            </pre>
          ),
          // Links
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent-primary hover:text-accent-tertiary underline transition-colors"
            >
              {children}
            </a>
          ),
          // Blockquotes
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-accent-primary/50 pl-4 italic text-foreground-secondary my-2 bg-background dark:bg-background/40 py-2 rounded-r">
              {children}
            </blockquote>
          ),
          // Tables
          table: ({ children }) => (
            <div className="overflow-x-auto mb-2 rounded-lg border border-border-light dark:border-border-dark">
              <table className="min-w-full divide-y divide-border-light dark:divide-border-dark">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-background dark:bg-background/60">{children}</thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-border-light dark:divide-border-dark">
              {children}
            </tbody>
          ),
          tr: ({ children }) => <tr>{children}</tr>,
          th: ({ children }) => (
            <th className="px-3 py-2 text-left text-xs font-semibold text-accent-primary">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 text-sm text-foreground-secondary">
              {children}
            </td>
          ),
          // Horizontal rule
          hr: () => (
            <hr className="my-4 border-border-light dark:border-border-dark" />
          ),
          // Strong/Bold
          strong: ({ children }) => (
            <strong className="font-bold text-foreground">
              {children}
            </strong>
          ),
          // Emphasis/Italic
          em: ({ children }) => (
            <em className="italic text-foreground-secondary">{children}</em>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
