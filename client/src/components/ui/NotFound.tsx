import { Frown } from "lucide-react";

interface NotFoundProps {
  message?: string;
}

export function NotFound({ message = "Not found" }: NotFoundProps) {
  return (
    <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-gray-400 text-xl">
        <div className="flex items-center gap-2">
          <p className="text-gray-400">😭 It's not you, it's us.</p>
        </div>
        <p className="text-gray-400">{message}</p>
      </div>
    </div>
  );
}
