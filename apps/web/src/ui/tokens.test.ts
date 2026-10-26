import prototype from "../../../../docs/prototype/wordcut.html?raw";
import indexHtml from "../../index.html?raw";
import appCss from "./app.css?raw";
import tokensCss from "./tokens.css?raw";

const PROTOTYPE_TOKENS = [
  "color-scheme",
  "--bg",
  "--panel",
  "--raised",
  "--hover",
  "--line",
  "--line-2",
  "--fg",
  "--muted",
  "--faint",
  "--accent",
  "--on-accent",
  "--ok",
  "--warn",
  "--danger",
  "--font-ui",
  "--font-mono",
  "--r",
];

function rootDeclarations(css: string): Map<string, string> {
  const root = /:root\s*\{([^}]*)\}/.exec(css)?.[1] ?? "";
  return new Map(
    root
      .split(";")
      .map((declaration) => declaration.split(/:(.*)/s).map((part) => part.trim()))
      .filter(([name]) => name)
      .map(([name, value]) => [name, value]),
  );
}

test("declares the prototype's colours and fonts with the same values", () => {
  const expected = rootDeclarations(prototype);
  const actual = rootDeclarations(tokensCss);

  expect(PROTOTYPE_TOKENS.map((name) => [name, actual.get(name)])).toEqual(
    PROTOTYPE_TOKENS.map((name) => [name, expected.get(name)]),
  );
});

test("loads nothing from another host", () => {
  expect([indexHtml, tokensCss, appCss].join("\n")).not.toMatch(/https?:\/\//);
});
