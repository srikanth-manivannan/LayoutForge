import { createContext, ReactNode, useContext, useRef } from "react";

import { DocumentManager } from "../document/DocumentManager";

const DocumentManagerCtx = createContext<DocumentManager | null>(null);

export function DocumentManagerProvider({ children }: { children: ReactNode }) {
  const managerRef = useRef<DocumentManager | null>(null);
  if (!managerRef.current) managerRef.current = new DocumentManager();
  return <DocumentManagerCtx.Provider value={managerRef.current}>{children}</DocumentManagerCtx.Provider>;
}

export function useDocumentManager(): DocumentManager {
  const manager = useContext(DocumentManagerCtx);
  if (!manager) throw new Error("useDocumentManager must be used within DocumentManagerProvider");
  return manager;
}
