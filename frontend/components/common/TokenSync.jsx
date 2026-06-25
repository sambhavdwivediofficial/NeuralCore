// components/common/TokenSync.jsx

'use client';

import { useEffect } from 'react';
import { AUTH_COOKIE_NAME } from '@/lib/constants';

export function TokenSync() {
  useEffect(() => {
    const token = localStorage.getItem('nc_token');
    if (token) {
      const cookieExists = document.cookie.split(';').some((c) => c.trim().startsWith(`${AUTH_COOKIE_NAME}=`));
      if (!cookieExists) {
        document.cookie = `${AUTH_COOKIE_NAME}=${token}; path=/; max-age=2592000; SameSite=Lax`;
      }
    }
  }, []);
  return null;
}
