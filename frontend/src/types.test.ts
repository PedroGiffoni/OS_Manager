import { describe, it, expect } from "vitest";
import { decimalToUnits, money } from "./types";
describe("conversão de valores de formulário", () => {
  it("preserva centavos e minutos inteiros", () => {
    expect(decimalToUnits("120,00", 100)).toBe(12000);
    expect(decimalToUnits("1.25", 60)).toBe(75);
    expect(decimalToUnits("8", 60)).toBe(480);
  });
  it("recusa valores inválidos e frações de minuto", () => {
    for (const value of ["NaN", "1e3", "-8", "0.01"])
      expect(() => decimalToUnits(value, 60)).toThrow();
  });
  it("apresenta moeda em reais", () =>
    expect(money(96000)).toContain("960,00"));
});

it("aceita qualquer minuto inteiro no formato HH:MM", () => {
  expect(decimalToUnits("0:01", 60)).toBe(1);
  expect(decimalToUnits("10:59", 60)).toBe(659);
  expect(() => decimalToUnits("1:60", 60)).toThrow();
});
