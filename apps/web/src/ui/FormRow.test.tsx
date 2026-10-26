import { render, screen } from "@testing-library/react";

import { FormRow } from "./FormRow";

test("names the control by the row's label and describes it beside", () => {
  render(
    <FormRow label="Modelo" description="Usado na sugestão automática." controlId="model">
      <input id="model" />
    </FormRow>,
  );

  const field = screen.getByRole("textbox", { name: "Modelo" });
  expect(field.closest(".srow")?.querySelector(".sd")).toHaveTextContent(
    "Usado na sugestão automática.",
  );
});
