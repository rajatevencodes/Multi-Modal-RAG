import React from "react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center font-sans dark:bg-black bg-white dark:text-white text-black">
      {children}
    </div>
  );
}
