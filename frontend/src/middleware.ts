import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';

// 保護対象のルートを定義
const isProtectedRoute = createRouteMatcher([
  '/',
  '/hitocari(.*)',
  '/api/proxy(.*)',
]);

export default clerkMiddleware(async (auth, req) => {
  // 保護されたルートへのアクセスの場合は認証必須
  if (isProtectedRoute(req)) {
    await auth.protect();
  }
});

export const config = {
  matcher: [
    // Skip Next.js internals and static files
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};