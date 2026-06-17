// app/settings/page.jsx

'use client';

import { useRouter } from 'next/navigation';
import { KeyRound, Shield, Users, ChevronRight, Sun, Moon, Monitor } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import { Label } from '@/components/common/Label';
import { Input } from '@/components/common/Input';
import { Button } from '@/components/common/Button';
import { Avatar } from '@/components/common/Avatar';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/common/Select';
import { useAuth } from '@/hooks/useAuth';
import { useSettingsContext } from '@/context/SettingsContext';
import { ROUTES } from '@/lib/routes';

const THEME_OPTIONS = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
];

export default function SettingsPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { theme, setTheme } = useSettingsContext();

  return (
    <AppShell>
      <div className="mx-auto flex max-w-2xl flex-col gap-5">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-foreground">Settings</h1>
          <p className="text-sm text-muted-foreground">
            Manage your account, security, team, and platform preferences
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <button
            onClick={() => router.push(ROUTES.SETTINGS_API_KEYS)}
            className="card-surface flex items-center justify-between p-4 text-left transition-colors hover:border-primary/40"
          >
            <div className="flex items-center gap-3">
              <KeyRound className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">API keys</span>
            </div>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
          <button
            onClick={() => router.push(ROUTES.SETTINGS_SECURITY)}
            className="card-surface flex items-center justify-between p-4 text-left transition-colors hover:border-primary/40"
          >
            <div className="flex items-center gap-3">
              <Shield className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Security</span>
            </div>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
          <button
            onClick={() => router.push(ROUTES.SETTINGS_USERS)}
            className="card-surface flex items-center justify-between p-4 text-left transition-colors hover:border-primary/40"
          >
            <div className="flex items-center gap-3">
              <Users className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Team</span>
            </div>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          </button>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Profile</CardTitle>
            <CardDescription>Your account information</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <Avatar name={user?.name} src={user?.avatar_url} size="lg" />
              <div className="flex flex-col">
                <span className="text-sm font-medium text-foreground">{user?.name}</span>
                <span className="text-xs text-muted-foreground">{user?.email}</span>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="full-name">Full name</Label>
                <Input id="full-name" defaultValue={user?.name} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" defaultValue={user?.email} disabled />
              </div>
            </div>

            <div className="flex justify-end">
              <Button size="sm">Save changes</Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Appearance</CardTitle>
            <CardDescription>Customize how NeuralCore looks on this device</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-1.5">
              <Label>Theme</Label>
              <Select value={theme} onValueChange={setTheme}>
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {THEME_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
