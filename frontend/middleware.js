// middleware.js

import { NextResponse } from 'next/server';
import { jwtVerify } from 'jose';

const PUBLIC_ROUTES = ['/login'];

const AUTH_COOKIE_NAME = 'nc_access_token';

async function verifyToken(token) {
  try {
    const secret = new TextEncoder().encode(
      process.env.JWT_PUBLIC_SECRET || 'neuralcore-dev-secret-key-min-32-characters-long'
    );
    const { payload } = await jwtVerify(token, secret, {
      algorithms: ['HS256', 'RS256'],
    });
    return payload;
  } catch (error) {
    return null;
  }
}

export async function middleware(request) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith('/_next') || pathname.startsWith('/api') || pathname.includes('.')) {
    return NextResponse.next();
  }

  const isPublicRoute = PUBLIC_ROUTES.some((route) => pathname.startsWith(route));
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;

  if (isPublicRoute) {
    if (token) {
      const payload = await verifyToken(token);
      if (payload) {
        return NextResponse.redirect(new URL('/dashboard', request.url));
      }
    }
    return NextResponse.next();
  }

  if (!token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  const payload = await verifyToken(token);

  if (!payload) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    const response = NextResponse.redirect(loginUrl);
    response.cookies.delete(AUTH_COOKIE_NAME);
    return response;
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-user-id', payload.sub || '');
  requestHeaders.set('x-user-role', payload.role || 'viewer');
  requestHeaders.set('x-tenant-id', payload.tenant_id || '');

  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|robots.txt|images).*)',
  ],
};
