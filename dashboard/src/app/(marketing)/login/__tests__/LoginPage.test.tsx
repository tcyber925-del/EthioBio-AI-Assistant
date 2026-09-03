import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "../page";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const createMock = vi.fn();
const prepareVerificationMock = vi.fn();
const setActiveMock = vi.fn();

vi.mock("@clerk/nextjs", () => ({
  useSignIn: () => ({
    signIn: { create: createMock, authenticateWithRedirect: vi.fn() },
    isLoaded: true,
    setActive: setActiveMock,
  }),
  useSignUp: () => ({
    signUp: {
      create: createMock,
      prepareVerification: prepareVerificationMock,
      attemptVerification: vi.fn(),
      authenticateWithRedirect: vi.fn(),
    },
    isLoaded: true,
    setActive: setActiveMock,
  }),
}));

vi.mock("@clerk/nextjs/errors", () => ({
  isClerkAPIResponseError: () => true,
}));

const messages = {
  login: {
    brand_short: "EthioSci",
    teacher_dashboard: "Teacher Dashboard",
    sign_in: "Sign In",
    create_account: "Create Account",
    create_and_sign_in: "Create & Sign In",
    please_wait: "Please wait…",
    already_have_account: "Already have an account?",
    new_teacher: "New here?",
    email: "Email",
    password: "Password",
    email_placeholder: "you@school.edu",
    password_placeholder: "••••••••",
    error: "Sign-in failed",
    continue_with_google: "Continue with Google",
    verify_email_title: "Verify your email",
    check_email: "Check your email for a verification code.",
    verify_code: "Verification code",
    verify_code_placeholder: "6-digit code",
    verify_button: "Verify",
  },
  errors: {
    retry: "Try again",
    generic: "Something went wrong",
  },
};

const renderPage = () =>
  render(
    <NextIntlClientProvider locale="en" messages={messages}>
      <LoginPage />
    </NextIntlClientProvider>,
  );

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    createMock.mockReset();
    prepareVerificationMock.mockReset();
    setActiveMock.mockReset();
  });

  it("shows the Clerk error message on invalid credentials (no raw object)", async () => {
    createMock.mockRejectedValueOnce({
      errors: [{ code: "form_password_incorrect", message: "Invalid credentials", longMessage: "Invalid credentials" }],
    });
    renderPage();
    fireEvent.change(screen.getByPlaceholderText("you@school.edu"), { target: { value: "a@b.c" } });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), { target: { value: "wrongpass" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await waitFor(() => expect(screen.getByText("Invalid credentials")).toBeInTheDocument());
    expect(screen.queryByText("[object Object]")).not.toBeInTheDocument();
  });

  it("prompts for email verification when sign-up is incomplete", async () => {
    createMock.mockResolvedValueOnce({ status: "missing_requirements" });
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Create Account" }));
    fireEvent.change(screen.getByPlaceholderText("you@school.edu"), { target: { value: "a@b.c" } });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), { target: { value: "strongpass123" } });
    fireEvent.click(screen.getByRole("button", { name: "Create & Sign In" }));
    await waitFor(() => expect(prepareVerificationMock).toHaveBeenCalledWith({ strategy: "email_code" }));
    expect(screen.getByText("Verify your email")).toBeInTheDocument();
  });
});