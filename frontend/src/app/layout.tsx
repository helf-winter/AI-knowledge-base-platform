import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';
import { SidebarShell } from '@/components/layout/sidebar-shell';
import { AuthGuard } from '@/components/auth/auth-guard';

export const metadata: Metadata = {
  title: '企业知识工作台',
  description: '面向企业知识管理、搜索与问答的工作台。',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>
          <AuthGuard>
            <SidebarShell>{children}</SidebarShell>
          </AuthGuard>
        </Providers>
      </body>
    </html>
  );
}
