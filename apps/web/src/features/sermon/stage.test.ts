import { runningTask } from "../../test/fixtures";
import { stageOf } from "./stage";

test.each([
  ["baixando", "Baixando"],
  ["sincronizando", "Sincronizando"],
  ["sugerindo", "Sugerindo"],
])("names the stage %s with a capital letter", (message, stage) => {
  expect(stageOf(runningTask({ progress_message: message }))).toBe(stage);
});

test.each([null, "", "  "])("names the stage Processando while the message is %j", (message) => {
  expect(stageOf(runningTask({ progress_message: message }))).toBe("Processando");
});

test("names the stage Processando before any task", () => {
  expect(stageOf(undefined)).toBe("Processando");
});
