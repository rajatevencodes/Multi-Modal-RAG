import Link from "next/link";

export default function HomePage() {
  return (
    <>
      <div className="min-h-screen bg-black text-white font-sans flex items-center justify-center">
        <div className="w-full max-w-md p-8 text-center space-y-6">
          <h1 className="text-3xl font-semibold">Welcome</h1>
          <div className="space-y-3">
            <Link
              href="/sign-in"
              className="block w-full bg-white text-black rounded-lg py-3 font-medium"
            >
              Sign In
            </Link>
            <Link
              href="/sign-up"
              className="block w-full border border-white/40 rounded-lg py-3 font-medium"
            >
              Create Account
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
