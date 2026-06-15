// app/layout.jsx

import { Inter, JetBrains_Mono } from 'next/font/google';
import { AuthProvider } from '@/context/AuthContext';
import { ProjectProvider } from '@/context/ProjectContext';
import { AgentProvider } from '@/context/AgentContext';
import { SettingsProvider } from '@/context/SettingsContext';
import { ToastProvider } from '@/components/common/Toast';
import { TooltipProvider } from '@/components/common/Tooltip';
import { APP_NAME } from '@/lib/constants';
import '@/styles/globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata = {
  title: {
    default: APP_NAME,
    template: `%s | ${APP_NAME}`,
  },
  description: 'Enterprise AI infrastructure platform for RAG, agents, and knowledge management.',
  icons: {
    icon: '/favicon.ico',
  },
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ffffff' },
    { media: '(prefers-color-scheme: dark)', color: '#0f0f12' },
  ],
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans`}>
        <SettingsProvider>
          <AuthProvider>
            <ProjectProvider>
              <AgentProvider>
                <TooltipProvider delayDuration={200}>
                  {children}
                  <ToastProvider />
                </TooltipProvider>
              </AgentProvider>
            </ProjectProvider>
          </AuthProvider>
        </SettingsProvider>
      </body>
    </html>
  );
}
