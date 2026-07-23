import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const hasAccess = request.cookies.has("access_token");
  const isLoginPage = request.nextUrl.pathname === "/login";
  const isPublic = request.nextUrl.pathname === "/";

  if (!hasAccess && !isLoginPage && !isPublic) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const response = NextResponse.next();
  response.headers.set("x-pathname", request.nextUrl.pathname);
  return response;
}

export const config = {
  matcher: ["/((?!_next|static|favicon.ico).*)"],
};
