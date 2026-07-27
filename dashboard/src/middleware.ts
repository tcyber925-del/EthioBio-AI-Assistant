import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasAccess = request.cookies.has("access_token");
  const isLoginPage = pathname === "/login";
  const isPublic = pathname === "/";
  const isApiPath = pathname.startsWith("/auth/") || pathname.startsWith("/api/");

  if (!hasAccess && !isLoginPage && !isPublic && !isApiPath) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const response = NextResponse.next();
  response.headers.set("x-pathname", request.nextUrl.pathname);
  return response;
}

export const config = {
  matcher: ["/((?!_next|static|favicon.ico).*)"],
};
