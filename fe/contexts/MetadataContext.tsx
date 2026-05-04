'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

/**
 * Metadata structure for multi-tenant filtering
 */
export interface ChatMetadata {
  tenant_id?: string;
  project_id?: string;
  task_id?: string;
  subtask_id?: string;
  user_id?: string;
  user_roles?: string[];
  knowledge_type?: string;
  [key: string]: any; // Allow additional custom fields
}

interface MetadataContextValue {
  metadata: ChatMetadata;
  setMetadata: (metadata: ChatMetadata) => void;
  updateMetadata: (updates: Partial<ChatMetadata>) => void;
  clearMetadata: () => void;
}

const MetadataContext = createContext<MetadataContextValue | undefined>(undefined);

interface MetadataProviderProps {
  children: ReactNode;
  initialMetadata?: ChatMetadata;
}

/**
 * MetadataProvider - Manages persistent metadata across the entire conversation
 *
 * Usage:
 * - Wrap your app/widget with this provider
 * - Set metadata once (from URL params, INIT message, etc.)
 * - Metadata persists across all messages in the session
 */
export function MetadataProvider({ children, initialMetadata = {} }: MetadataProviderProps) {
  const [metadata, setMetadataState] = useState<ChatMetadata>(initialMetadata);

  const setMetadata = useCallback((newMetadata: ChatMetadata) => {
    console.log('[MetadataContext] Setting metadata:', newMetadata);
    setMetadataState(newMetadata);
  }, []);

  const updateMetadata = useCallback((updates: Partial<ChatMetadata>) => {
    console.log('[MetadataContext] Updating metadata:', updates);
    setMetadataState((prev) => ({ ...prev, ...updates }));
  }, []);

  const clearMetadata = useCallback(() => {
    console.log('[MetadataContext] Clearing metadata');
    setMetadataState({});
  }, []);

  return (
    <MetadataContext.Provider value={{ metadata, setMetadata, updateMetadata, clearMetadata }}>
      {children}
    </MetadataContext.Provider>
  );
}

/**
 * useMetadata hook - Access and modify persistent metadata
 */
export function useMetadata() {
  const context = useContext(MetadataContext);
  if (context === undefined) {
    throw new Error('useMetadata must be used within a MetadataProvider');
  }
  return context;
}
