// app/layout.jsx

import { Inter, JetBrains_Mono } from 'next/font/google';
import { AuthProvider } from '@/context/AuthContext';
import { ProjectProvider } from '@/context/ProjectContext';
import { AgentProvider } from '@/context/AgentContext';
import { SettingsProvider } from '@/context/SettingsContext';
import { ToastProvider } from '@/components/common/Toast';
import { TooltipProvider } from '@/components/common/Tooltip';
import { TokenSync } from '@/components/common/TokenSync';
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
    icon: '/image.png',
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
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function () {
                try {
                  var theme = window.localStorage.getItem('nc_theme') || 'system';
                  var isDark =
                    theme === 'dark' ||
                    (theme === 'system' &&
                      window.matchMedia('(prefers-color-scheme: dark)').matches);
                  if (isDark) {
                    document.documentElement.classList.add('dark');
                  } else {
                    document.documentElement.classList.remove('dark');
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans`}>
        <SettingsProvider>
          <AuthProvider>
            <TokenSync />
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
