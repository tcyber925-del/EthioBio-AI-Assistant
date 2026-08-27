import dynamic from 'next/dynamic';
import { BioPattern } from '@/components/dashboard-v2/BioPattern';
import { ShellPadding } from '@/components/dashboard-v2/ShellPadding';
import { SubjectGradeProvider } from '@/context/SubjectGradeContext';
import { SubjectGradeSelector } from '@/components/SubjectGradeSelector';

const SidebarV2 = dynamic(() => import('@/components/dashboard-v2/SidebarV2').then(m => m.SidebarV2), { ssr: false });

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SubjectGradeProvider>
      <div className="flex h-screen overflow-hidden">
        <SidebarV2 />
        <div className="relative flex flex-1 flex-col overflow-hidden min-w-0">
          <BioPattern />
          <div className="relative z-10 shrink-0 flex justify-end px-5 pt-3 sm:px-8 lg:px-10">
            <SubjectGradeSelector />
          </div>
          <ShellPadding>{children}</ShellPadding>
        </div>
      </div>
    </SubjectGradeProvider>
  );
}
