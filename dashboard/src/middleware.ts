import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

const isPublicRoute = createRouteMatcher([
  "/",
  "/login(.*)",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/sso-callback(.*)",
  "/auth(.*)",
  "/api(.*)",
]);

export default clerkMiddleware(async (auth, request) => {
  if (!isPublicRoute(request)) {
    const { userId } = await auth()
    if (!userId) {
      const url = new URL('/sign-in', request.url)
      url.searchParams.set('redirect_url', request.nextUrl.pathname + request.nextUrl.search)
      return NextResponse.redirect(url)
    }
  }
  const response = NextResponse.next();
  response.headers.set("x-pathname", request.nextUrl.pathname);
  return response;
});

export const config = {
  matcher: ["/((?!_next|static|favicon.ico).*)", "/(api|trpc)(.*)", "/__clerk/:path*"],
};