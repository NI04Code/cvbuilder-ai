import { auth, signOut } from "@/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { FileText, LayoutDashboard, UserCircle, FileSignature, LogOut } from "lucide-react";
import styles from "./layout.module.css";
import React from "react";
import { SessionWatcher } from "@/components/SessionWatcher";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();

  if (!session?.user) {
    redirect("/login");
  }

  return (
    <div className={styles.layout}>
      <SessionWatcher sessionError={(session as any)?.error} />
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <FileText size={28} className={styles.logoIcon} />
          <span className={styles.logoText}>
            JobSeek <span className="gradient-text">AI</span>
          </span>
        </div>

        <nav className={styles.nav}>
          <Link href="/dashboard" className={styles.navLink}>
            <LayoutDashboard size={20} />
            Dashboard
          </Link>
          <Link href="/profile" className={styles.navLink}>
            <UserCircle size={20} />
            My Profile
          </Link>
          <Link href="/generate" className={styles.navLink}>
            <FileSignature size={20} />
            Generate CV
          </Link>
        </nav>

        <div className={styles.userProfile}>
          <div className={styles.avatar}>
            {session.user.image ? (
              <img src={session.user.image} alt={session.user.name || "User"} />
            ) : (
              <span>{session.user.name?.charAt(0) || "U"}</span>
            )}
          </div>
          <div className={styles.userInfo}>
            <span className={styles.userName}>{session.user.name}</span>
            <span className={styles.userEmail}>{session.user.email}</span>
          </div>
          <form action={async () => {
            "use server";
            await signOut({ redirectTo: "/" });
          }}>
            <button type="submit" title="Sign Out" style={{ color: '#94a3b8', cursor: 'pointer', padding: '0.5rem' }}>
              <LogOut size={18} />
            </button>
          </form>
        </div>
      </aside>

      <main className={styles.main}>
        {children}
      </main>
    </div>
  );
}
