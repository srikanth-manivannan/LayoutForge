import { useCallback, useEffect, useState } from "react";

import { checkEnvironment, EnvironmentCheckResult } from "./checkEnvironment";

export function useEnvironmentCheck() {
  const [result, setResult] = useState<EnvironmentCheckResult | null>(null);
  const [isChecking, setIsChecking] = useState(true);

  const recheck = useCallback(async () => {
    setIsChecking(true);
    setResult(await checkEnvironment());
    setIsChecking(false);
  }, []);

  useEffect(() => {
    recheck();
  }, [recheck]);

  return { result, isChecking, recheck };
}
