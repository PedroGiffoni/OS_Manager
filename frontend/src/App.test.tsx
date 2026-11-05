import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Login } from "./App";
describe("entrada individual", () => {
  it("valida os campos sem chamar a API", async () => {
    const fetcher = vi.spyOn(globalThis, "fetch");
    render(<Login onLogin={vi.fn()} />);
    fireEvent.click(
      screen.getByRole("button", { name: /Entrar na Gestão de Demandas/ }),
    );
    await waitFor(() =>
      expect(screen.getByText("Informe o usuário.")).toBeInTheDocument(),
    );
    expect(fetcher).not.toHaveBeenCalled();
    fetcher.mockRestore();
  });
});
