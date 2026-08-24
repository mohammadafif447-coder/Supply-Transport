"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/admin/dashboard", label: "Orders" },
  { href: "/admin/drivers", label: "Drivers & Vehicles" },
  { href: "/admin/commission-rules", label: "Commission Rules" },
];

export function AdminNav() {
  const pathname = usePathname();

  return (
    <nav className="flex gap-1 rounded-lg bg-iron p-1">
      {LINKS.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={`rounded-md px-3 py-2 text-sm font-medium transition ${
            pathname === link.href ? "bg-lime text-iron" : "text-white hover:bg-white/10"
          }`}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
