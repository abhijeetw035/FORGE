'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { LayoutDashboard, Activity, History, BrainCircuit, Users, ArrowLeft } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}

export default function RepositoryLayout({ children, params }: LayoutProps) {
  const pathname = usePathname();
  const [id, setId] = useState<string>('');

  useEffect(() => {
    params.then(p => setId(p.id));
  }, [params]);

  const menuItems = [
    {
      name: 'Overview',
      href: `/repositories/${id}`,
      icon: LayoutDashboard,
      exact: true
    },
    {
      name: 'Entropy Map',
      href: `/repositories/${id}/heatmap`,
      icon: Activity
    },
    {
      name: 'Evolution',
      href: `/repositories/${id}/timeline`,
      icon: History
    },
    {
      name: 'Risk Forecast',
      href: `/repositories/${id}/risk`,
      icon: BrainCircuit
    },
    {
      name: 'Team Stats',
      href: `/repositories/${id}/team`,
      icon: Users
    }
  ];

  const isActive = (href: string, exact?: boolean) => {
    if (exact) {
      return pathname === href;
    }
    return pathname.startsWith(href);
  };

  return (
    <div className="flex min-h-screen">
      <aside className="w-64 bg-zinc-950 border-r border-zinc-800 fixed h-screen overflow-y-auto">
        <div className="p-6">
          <Link 
            href="/dashboard"
            className="flex items-center gap-2 px-4 py-3 mb-6 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-900 transition-all duration-200 border border-zinc-800"
          >
            <ArrowLeft className="w-5 h-5" />
            <span className="font-medium">All Repositories</span>
          </Link>

          <h2 className="text-lg font-semibold text-white mb-4">Repository</h2>
          <nav className="space-y-2">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href, item.exact);
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`
                    flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200
                    ${active 
                      ? 'bg-blue-500/10 text-blue-400 border-r-2 border-blue-500' 
                      : 'text-zinc-400 hover:text-white hover:bg-zinc-900'
                    }
                  `}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </aside>

      <main className="flex-1 ml-64 overflow-y-auto">
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
