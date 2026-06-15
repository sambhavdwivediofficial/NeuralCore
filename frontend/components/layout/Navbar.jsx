// components/layout/Navbar.jsx

'use client';

import { useRouter } from 'next/navigation';
import { Bell, LogOut, Moon, Sun, Monitor, User, Settings, Command } from 'lucide-react';
import { Breadcrumbs } from '@/components/layout/Breadcrumbs';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/common/Avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuShortcut,
} from '@/components/common/DropdownMenu';
import { Button } from '@/components/common/Button';
import { useAuth } from '@/hooks/useAuth';
import { useSettingsContext } from '@/context/SettingsContext';
import { useAlerts } from '@/hooks/useMonitoring';
import { ROUTES } from '@/lib/routes';
import { initials } from '@/lib/utils';

export function Navbar() {
  const router = useRouter();
  const { user, signOut } = useAuth();
  const { theme, setTheme } = useSettingsContext();
  const { alerts } = useAlerts({ status: 'open', page_size: 1 });

  const unresolvedCount = alerts?.length || 0;

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-4 border-b border-border bg-background/95 px-4 backdrop-blur-sm">
      <Breadcrumbs />

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="hidden gap-2 text-muted-foreground sm:flex"
          onClick={() => {
            const event = new KeyboardEvent('keydown', { key: 'k', metaKey: true });
            window.dispatchEvent(event);
          }}
        >
          <Command className="h-3.5 w-3.5" />
          <span>Search</span>
          <span className="kbd ml-1">⌘K</span>
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-4 w-4" />
              {unresolvedCount > 0 ? (
                <span className="absolute right-1.5 top-1.5 flex h-2 w-2 rounded-full bg-destructive" />
              ) : null}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-72">
            <DropdownMenuLabel>Alerts</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {unresolvedCount === 0 ? (
              <div className="px-2 py-4 text-center text-xs text-muted-foreground">
                No active alerts
              </div>
            ) : (
              alerts.slice(0, 5).map((alert) => (
                <DropdownMenuItem
                  key={alert.id}
                  onClick={() => router.push(ROUTES.MONITORING_ALERTS)}
                  className="flex-col items-start gap-0.5"
                >
                  <span className="text-sm font-medium">{alert.title}</span>
                  <span className="text-xs text-muted-foreground">{alert.service}</span>
                </DropdownMenuItem>
              ))
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => router.push(ROUTES.MONITORING_ALERTS)}>
              View all alerts
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon">
              {theme === 'dark' ? (
                <Moon className="h-4 w-4" />
              ) : theme === 'light' ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Monitor className="h-4 w-4" />
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setTheme('light')}>
              <Sun className="h-3.5 w-3.5" />
              Light
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme('dark')}>
              <Moon className="h-3.5 w-3.5" />
              Dark
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme('system')}>
              <Monitor className="h-3.5 w-3.5" />
              System
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 rounded-md p-1 transition-colors hover:bg-accent">
              <Avatar className="h-7 w-7">
                <AvatarImage src={user?.avatar_url} alt={user?.name} />
                <AvatarFallback seed={user?.email}>{initials(user?.name)}</AvatarFallback>
              </Avatar>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="flex flex-col gap-0.5">
              <span className="text-sm font-medium text-foreground">{user?.name}</span>
              <span className="text-xs text-muted-foreground">{user?.email}</span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => router.push(ROUTES.SETTINGS)}>
              <User className="h-3.5 w-3.5" />
              Profile
              <DropdownMenuShortcut>⌘P</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(ROUTES.SETTINGS)}>
              <Settings className="h-3.5 w-3.5" />
              Settings
              <DropdownMenuShortcut>⌘,</DropdownMenuShortcut>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={signOut} className="text-destructive focus:text-destructive">
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
