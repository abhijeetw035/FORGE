'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { LayoutDashboard, Activity, History, BrainCircuit, Users, ArrowLeft, GitBranch, Menu, Lightbulb } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}

export default function RepositoryLayout({ children, params }: LayoutProps) {
  const pathname = usePathname();
  const [id, setId] = useState<string>('');
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    params.then(p => setId(p.id));
  }, [params]);

  const menuItems = [
    { name: 'Overview',      href: `/repositories/${id}`,             icon: LayoutDashboard, exact: true },
    { name: 'File Analytics',href: `/repositories/${id}/heatmap`,     icon: Activity },
    { name: 'Evolution',     href: `/repositories/${id}/timeline`,    icon: History },
    { name: 'Risk Forecast', href: `/repositories/${id}/risk`,        icon: BrainCircuit },
    { name: 'Functions',     href: `/repositories/${id}/functions`,   icon: GitBranch },
    { name: 'Team Stats',    href: `/repositories/${id}/team`,        icon: Users },
    { name: 'Insights',      href: `/repositories/${id}/insights`,    icon: Lightbulb },
  ];

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname.startsWith(href);

  const sidebarW = collapsed ? 'w-16' : 'w-64';
  const mainML   = collapsed ? 'ml-16' : 'ml-64';

  return (
    <div className="flex min-h-screen">
      <aside className={`${sidebarW} bg-zinc-950 border-r border-zinc-800 fixed h-screen overflow-y-auto transition-all duration-200 flex flex-col`}>

        <div className={`flex-1 ${collapsed ? 'px-2 py-4' : 'p-6'}`}>

          {/* Back link */}
          <Link
            href="/dashboard"
            className={`flex items-center gap-2 px-3 py-3 mb-3 rounded-lg text-white bg-zinc-900/50 hover:bg-zinc-900 border border-zinc-700 hover:border-zinc-600 transition-all duration-200 ${collapsed ? 'justify-center' : ''}`}
            title="All Repositories"
          >
            <ArrowLeft className="w-5 h-5 shrink-0" />
            {!collapsed && <span className="font-medium truncate">All Repositories</span>}
          </Link>

          {/* Hamburger toggle — sits below the back button */}
          <button
            onClick={() => setCollapsed(v => !v)}
            className={`flex items-center gap-2 px-3 py-2 mb-5 w-full rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-900 transition-all duration-200 ${collapsed ? 'justify-center' : ''}`}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <Menu className="w-5 h-5 shrink-0" />
            {!collapsed && <span className="text-sm font-medium">Collapse</span>}
          </button>

          {!collapsed && (
            <h2 className="text-lg font-semibold text-white mb-4">Repository</h2>
          )}

          <nav className="space-y-1">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href, item.exact);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  title={item.name}
                  className={`
                    flex items-center gap-3 px-3 py-3 rounded-lg transition-all duration-200
                    ${collapsed ? 'justify-center' : ''}
                    ${active
                      ? 'bg-blue-500/10 text-blue-400 border-r-2 border-blue-500'
                      : 'text-zinc-400 hover:text-white hover:bg-zinc-900'}
                  `}
                >
                  <Icon className="w-5 h-5 shrink-0" />
                  {!collapsed && <span className="font-medium">{item.name}</span>}
                </Link>
              );
            })}
          </nav>
        </div>
      </aside>

      <main className={`flex-1 ${mainML} overflow-y-auto transition-all duration-200`}>
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  );
}

