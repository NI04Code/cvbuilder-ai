"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, UserCircle, FileSignature, Target } from "lucide-react";
import styles from "@/app/(dashboard)/layout.module.css";

const NAV_ITEMS = [
  { href: "/dashboard", label: "CV History", icon: LayoutDashboard },
  { href: "/profile", label: "Base Profile", icon: UserCircle },
  { href: "/generate", label: "Tailor CV", icon: FileSignature },
  { href: "/ats-checker", label: "ATS Checker", icon: Target },
];

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <nav className={styles.nav}>
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const isActive = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            className={`${styles.navLink} ${isActive ? styles.navLinkActive : ""}`}
          >
            <Icon size={18} strokeWidth={1.75} className={styles.navIcon} />
            <span>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

