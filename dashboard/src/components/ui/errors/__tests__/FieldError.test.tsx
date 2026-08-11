import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";
import { FieldError } from "../FieldError";

const messages = {
  errors: {
    validation: {
      missing: "Please fill in the {field} field.",
      value_error: "Please enter a valid value for the {field} field.",
    },
  },
};

describe("FieldError", () => {
  it("renders each message with the field param", () => {
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <FieldError id="email-error" field="email" messages={["errors.validation.missing", "errors.validation.value_error"]} />
      </NextIntlClientProvider>,
    );
    expect(screen.getByText("Please fill in the email field.")).toBeInTheDocument();
    expect(screen.getByText("Please enter a valid value for the email field.")).toBeInTheDocument();
  });
  it("associates with the input via aria-describedby id", () => {
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <div>
          <input type="text" aria-describedby="email-error" />
          <FieldError id="email-error" field="email" messages={["errors.validation.missing"]} />
        </div>
      </NextIntlClientProvider>,
    );
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-describedby", "email-error");
  });
});
