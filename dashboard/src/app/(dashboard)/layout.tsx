import NextDynamic from 'next/dynamic';
import { BioPattern } from '@/components/dashboard-v2/BioPattern';
import { ShellPadding } from '@/components/dashboard-v2/ShellPadding';

const SidebarV2 = NextDynamic(() => import('@/components/dashboard-v2/SidebarV2').then(m => m.SidebarV2), { ssr: false });

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden">
      <SidebarV2 />
      <div className="relative flex flex-1 flex-col overflow-hidden min-w-0">
        <BioPattern />
        <ShellPadding>{children}</ShellPadding>
      </div>
    </div>
  );
}
