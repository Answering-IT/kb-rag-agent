import { Chat } from '@/components/chat';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col bg-gradient-to-br from-background via-background-secondary to-background">
      {/* Header */}
      <header className="border-b border-border-light dark:border-border-dark bg-background-secondary dark:bg-background-secondary/50 backdrop-blur-md sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex items-baseline gap-2">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-accent-primary via-accent-tertiary to-accent-primary bg-clip-text text-transparent">
              ProcessApp RAG
            </h1>
            <span className="text-foreground-secondary font-mono text-xs px-2 py-1 rounded-md bg-background/50 dark:bg-background/30">
              v1.0
            </span>
          </div>
          <p className="text-sm text-foreground-secondary mt-2">
            AI-powered document assistant powered by AWS Bedrock
          </p>
        </div>
      </header>

      {/* Main content */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6">
        <div className="h-[calc(100vh-160px)] bg-background-secondary dark:bg-background-secondary/80 rounded-xl shadow-xl border border-border-light dark:border-border-dark overflow-hidden">
          <Chat />
        </div>
      </div>

      {/* Footer accent */}
      <div className="h-px bg-gradient-to-r from-transparent via-accent-primary/20 to-transparent" />
    </main>
  );
}
