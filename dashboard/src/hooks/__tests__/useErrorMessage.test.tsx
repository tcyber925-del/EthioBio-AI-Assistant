import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";
import { errorMessageKeys, useErrorMessage } from "../useErrorMessage";

const error = {
  category: "authentication" as const,
  code: "auth_invalid_credentials",
  status: 401,
  retryable: false,
};

describe("errorMessageKeys", () => {
  it("resolves known codes to the codes.* key", () => {
    expect(errorMessageKeys(error).key).toBe("errors.codes.auth_invalid_credentials");
  });
  it("unknown code falls back to http.<status>", () => {
    expect(errorMessageKeys({ ...error, code: "bogus_xyz" }).key).toBe("errors.http.401");
  });
  it("no status falls back to categories.<category>", () => {
    expect(errorMessageKeys({ category: "network", retryable: true }).key).toBe("errors.categories.network");
  });
  it("complete fallback chain ends at errors.generic", () => {
    expect(errorMessageKeys({ category: "unknown", retryable: false }).key).toBe("errors.generic");
  });
});

describe("useErrorMessage (renders, no raw output)", () => {
  it("renders the catalog message for a known code", () => {
    let text = "";
    function Probe() {
      text = useErrorMessage(error);
      return null;
    }
    render(
      <NextIntlClientProvider locale="en" messages={{ errors: { codes: { auth_invalid_credentials: "Invalid email or password. Please check your credentials and try again." } } }}>
        <Probe />
      </NextIntlClientProvider>,
    );
    expect(text).toContain("Invalid email or password");
  });

  it("returns empty string for null/undefined", () => {
    let text = "x";
    function Probe() {
      text = useErrorMessage(null);
      return null;
    }
    render(
      <NextIntlClientProvider locale="en" messages={{}}>
        <Probe />
      </NextIntlClientProvider>,
    );
    expect(text).toBe("");
  });
});