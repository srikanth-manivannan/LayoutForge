import { createContext, ReactNode, useContext, useRef } from "react";

import { createBuiltinCommands } from "../commands/builtins";
import { CommandRegistry } from "../commands/CommandRegistry";

const CommandRegistryCtx = createContext<CommandRegistry | null>(null);

export function CommandProvider({ children }: { children: ReactNode }) {
  const registryRef = useRef<CommandRegistry | null>(null);
  if (!registryRef.current) {
    const registry = new CommandRegistry();
    createBuiltinCommands().forEach((command) => registry.register(command));
    registryRef.current = registry;
  }
  return <CommandRegistryCtx.Provider value={registryRef.current}>{children}</CommandRegistryCtx.Provider>;
}

export function useCommandRegistry(): CommandRegistry {
  const registry = useContext(CommandRegistryCtx);
  if (!registry) throw new Error("useCommandRegistry must be used within CommandProvider");
  return registry;
}
