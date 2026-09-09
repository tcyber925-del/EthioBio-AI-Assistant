import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "../page";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pushMock }) }));

const createMock = vi.fn();
const setActiveMock = vi.fn();
const authenticateWithRedirectMock = vi.fn();

vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({ isSignedIn: false }),
  useSignIn: () => ({
    signIn: { create: createMock, authenticateWithRedirect: authenticateWithRedirectMock },
    isLoaded: true,
    setActive: setActiveMock,
  }),
}));

vi.mock("@clerk/nextjs/errors", () => ({
  isClerkAPIResponseError: () => true,
}));

const messages = {
  login: {
    sign_in: "Sign In",
    sign_in_subtitle: "Log in to continue learning.",
    email: "Email",
    password: "Password",
    email_placeholder: "you@school.edu",
    password_placeholder: "••••••••",
    please_wait: "Please wait…",
    error: "Sign-in failed",
    continue_with_google: "Continue with Google",
    continue_with_microsoft: "Continue with Microsoft",
    or_email: "or sign in with email",
    forgot_password: "Forgot password?",
    new_here: "New to EthioSci?",
    create_account: "Create an account",
    hide_password: "Hide password",
    show_password: "Show password",
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
    pushMock.mockReset();
    createMock.mockReset();
    setActiveMock.mockReset();
    authenticateWithRedirectMock.mockReset();
    vi.stubGlobal("fetch", vi.fn());
  });

  it("renders sign-in controls and links (no register/claim UI)", () => {
    renderPage();
    expect(screen.getByRole("textbox", { name: /Email/ })).toBeVisible();
    expect(screen.getByLabelText(/Password/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Sign In" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Continue with Google" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Continue with Microsoft" })).toBeVisible();
    expect(screen.getByRole("link", { name: "Forgot password?" })).toHaveAttribute(
      "href",
      "/forgot-password",
    );
    expect(screen.getByRole("link", { name: "Create an account" })).toHaveAttribute(
      "href",
      "/sign-up",
    );
    expect(screen.queryByText("Create & Sign In")).not.toBeInTheDocument();
  });

  it("signs in and resolves to the role dashboard", async () => {
    createMock.mockResolvedValueOnce({ status: "complete", createdSessionId: "sess_1" });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        text: async () => JSON.stringify({ role_claimed: true, onboarding_completed: true }),
      }),
    );
    renderPage();
    fireEvent.change(screen.getByPlaceholderText("you@school.edu"), {
      target: { value: "a@b.c" },
    });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), {
      target: { value: "correct-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));
    await waitFor(() =>
      expect(createMock).toHaveBeenCalledWith({
        identifier: "a@b.c",
        password: "correct-password",
      }),
    );
    await waitFor(() => expect(setActiveMock).toHaveBeenCalledWith({ session: "sess_1" }));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/v2/overview"));
  });

  it("starts Google OAuth with the sso-callback redirect", async () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
    expect(authenticateWithRedirectMock).toHaveBeenCalledWith({
      strategy: "oauth_google",
      redirectUrl: "/sso-callback",
      redirectUrlComplete: "/v2/overview",
    });
  });

  it("shows the Clerk error message on invalid credentials", async () => {
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
});