import { useEffect, useState } from "react";
export function useTheme() {
  const [dark, setDark] = useState(() => {
    try {
      return localStorage.getItem("gestao-demandas-theme") === "dark";
    } catch {
      return false;
    }
  });
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    document.documentElement.style.colorScheme = dark ? "dark" : "light";
    try {
      localStorage.setItem("gestao-demandas-theme", dark ? "dark" : "light");
    } catch {
      /* Storage may be blocked. */
    }
  }, [dark]);
  return [dark, () => setDark((current) => !current)] as const;
}
