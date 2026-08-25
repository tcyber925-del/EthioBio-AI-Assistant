import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { useRouter } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "../page";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const messages = {
  login: {
    brand_short: "EthioSci", teacher_dashboard: "Teacher Dashboard", sign_in: "Sign In",
    create_account: "Create Account", email: "Email", password: "Password",
    email_placeholder: "you@school.edu", password_placeholder: "••••••••",
    register_as: "Register as", teacher: "Teacher", student: "Student", parent: "Parent",
    please_wait: "Please wait…", create_and_sign_in: "Create & Sign In",
    already_have_account: "Already have an account?", new_teacher: "New here?",
    continue_with_google: "Continue with Google", login_telegram: "Log in with Telegram",
    telegram_otp: "Telegram OTP", telegram_id: "Telegram ID", telegram_id_hint: "123456789",
    otp_code: "OTP Code", send_otp: "Send OTP", sending: "Sending…",
    verify_login: "Verify & Log In", verifying: "Verifying…", back_to_email: "Back",
    error: "Sign-in failed", telegram_error: "Telegram sign-in failed",
  },
  errors: {
    retry: "Try again",
    codes: { auth_invalid_credentials: "Invalid email or password. Please check your credentials and try again." },
    http: { "500": "Something went wrong on our side. Please try again in a moment." },
  },
};

describe("LoginPage", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders a translated error alert on invalid credentials (no raw object)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      text: () => Promise.resolve(JSON.stringify({ error: { code: "auth_invalid_credentials", detail: "Invalid email or password", context: {} } })),
    }));
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <LoginPage />
      </NextIntlClientProvider>,
    );
    fireEvent.change(screen.getByPlaceholderText("you@school.edu"), { target: { value: "a@b.c" } });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), { target: { value: "wrongpass" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await waitFor(() =>
      expect(screen.getByText(/Invalid email or password/)).toBeInTheDocument(),
    );
    expect(screen.queryByText("[object Object]")).not.toBeInTheDocument();
    expect(screen.queryByText("auth_invalid_credentials")).not.toBeInTheDocument();
  });

  it("renders a translated alert on backend 500", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve(JSON.stringify({ detail: "pg_dump failed (exit 1)" })),
    }));
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <LoginPage />
      </NextIntlClientProvider>,
    );
    fireEvent.change(screen.getByPlaceholderText("you@school.edu"), { target: { value: "a@b.c" } });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), { target: { value: "rightpass" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await waitFor(() => expect(screen.getByText(/Something went wrong on our side/)).toBeInTheDocument());
    expect(screen.queryByText(/pg_dump/)).not.toBeInTheDocument();
  });
});
