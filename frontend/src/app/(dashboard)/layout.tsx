import { auth, signOut } from "@/auth";
import Link from "next/link";
import { FileText, LogOut } from "lucide-react";
import styles from "./layout.module.css";
import React from "react";
import { SessionWatcher } from "@/components/SessionWatcher";
import { SidebarNav } from "@/components/SidebarNav";
import { ThemeToggle } from "@/components/ThemeToggle";
import { DocumentGenerationProvider } from "@/context/DocumentGenerationContext";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();
  const user = session?.user;

  if (!user || (session as any)?.error) {
    return (
      <DocumentGenerationProvider hasSidebar={false}>
        <SessionWatcher sessionError={(session as any)?.error} />
        {children}
      </DocumentGenerationProvider>
    );
  }

  return (
    <div className={styles.layout}>
      <SessionWatcher sessionError={(session as any)?.error} />
      <aside className={styles.sidebar}>
        <div className={styles.sidebarTop}>
          <Link href="/dashboard" className={styles.logo}>
            <FileText size={20} strokeWidth={1.75} className={styles.logoIcon} />
            <span className={styles.logoText}>CVBuilder</span>
            <span className={styles.logoTag}>ATS</span>
          </Link>
          <ThemeToggle />
        </div>

        <SidebarNav />

        <div className={styles.userProfile}>
          <div className={styles.avatar}>
            {user.image ? (
              <img src={user.image} alt={user.name || "User"} />
            ) : (
              <span>{user.name?.charAt(0) || "U"}</span>
            )}
          </div>
          <div className={styles.userInfo}>
            <span className={styles.userName}>{user.name}</span>
            <span className={styles.userEmail}>{user.email}</span>
          </div>
          <form
            action={async () => {
              "use server";
              await signOut({ redirectTo: "/" });
            }}
          >
            <button
              type="submit"
              title="Sign Out"
              aria-label="Sign Out"
              className={styles.signOutBtn}
            >
              <LogOut size={16} strokeWidth={1.75} />
            </button>
          </form>
        </div>
      </aside>

      <main className={styles.main}>
        <DocumentGenerationProvider hasSidebar={true}>{children}</DocumentGenerationProvider>
      </main>
    </div>
  );
}
