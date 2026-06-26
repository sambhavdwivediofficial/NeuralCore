// frontend/middleware.js

import { NextResponse } from 'next/server';
import { jwtVerify, importSPKI } from 'jose';
import { AUTH_COOKIE_NAME } from '@/lib/constants';

const PUBLIC_ROUTES = [
  '/',
  '/login',
  '/login/mfa',
  '/signup',
  '/forgot-password',
  '/verify-email',
  '/auth/callback',
  '/terms',
  '/privacy',
  '/security',
  '/changelog',
  '/architecture',
];

const PUBLIC_PREFIXES = ['/reset-password/', '/accept-invite/'];

let _cachedKey = null;

async function getVerifyKey() {
  if (_cachedKey) return _cachedKey;
  const secret = process.env.JWT_PUBLIC_SECRET || '';
  if (secret.includes('BEGIN PUBLIC KEY')) {
    _cachedKey = await importSPKI(secret, 'RS256');
  } else {
    _cachedKey = new TextEncoder().encode(
      secret || 'neuralcore-dev-secret-key-min-32-characters-long'
    );
  }
  return _cachedKey;
}

async function verifyToken(token) {
  try {
    const key = await getVerifyKey();
    const { payload } = await jwtVerify(token, key);
    return payload;
  } catch {
    return null;
  }
}

function isPublicPath(pathname) {
  if (PUBLIC_ROUTES.includes(pathname)) return true;
  if (PUBLIC_PREFIXES.some((p) => pathname.startsWith(p))) return true;
  return false;
}

export async function middleware(request) {
  const { pathname } = request.nextUrl;

  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  const isPublic = isPublicPath(pathname);
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;

  if (isPublic) {
    if (token) {
      const payload = await verifyToken(token);
      if (payload) {
        const authOnlyPages = ['/', '/login', '/signup', '/forgot-password', '/login/mfa'];
        if (authOnlyPages.includes(pathname)) {
          const dest = payload.tenant_id ? '/dashboard' : '/onboarding';
          return NextResponse.redirect(new URL(dest, request.url));
        }
      }
    }
    return NextResponse.next();
  }

  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  const payload = await verifyToken(token);

  if (!payload) {
    const response = NextResponse.redirect(new URL('/login', request.url));
    response.cookies.delete(AUTH_COOKIE_NAME);
    return response;
  }

  if (!payload.tenant_id && pathname !== '/onboarding' && payload.role !== 'super_admin') {
    return NextResponse.redirect(new URL('/onboarding', request.url));
  }

  if (pathname.startsWith('/admin') && payload.role !== 'super_admin') {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-user-id', String(payload.sub ?? ''));
  requestHeaders.set('x-user-role', String(payload.role ?? 'viewer'));
  requestHeaders.set('x-tenant-id', String(payload.tenant_id ?? ''));

  return NextResponse.next({ request: { headers: requestHeaders } });
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|robots.txt|images).*)'],
};
