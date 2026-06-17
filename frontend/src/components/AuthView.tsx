"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface AuthViewProps {
  onSuccess: (token: string) => void;
}

export default function AuthView({ onSuccess }: AuthViewProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isLogin) {
        const res = await api.login(email, password);
        localStorage.setItem("helix_decidex_auth_token", res.access_token);
        onSuccess(res.access_token);
      } else {
        const res = await api.signup(email, password);
        localStorage.setItem("helix_decidex_auth_token", res.access_token);
        onSuccess(res.access_token);
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed. Access denied.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white font-mono flex flex-col items-center justify-center p-4">
      {/* Top Banner / ASCII decoration */}
      <div className="w-full max-w-md mb-8 text-center select-none text-zinc-500">
        <pre className="text-xs leading-tight">
{`=========================================
  ____  ____   ___    _ _____ ____ _____ 
 |  _ \\|  _ \\ / _ \\  | | ____/ ___|_   _|
 | |_) | |_) | | | |_| |  _| | |     | |  
 |  __/|  _ <| |_| |_| | |___| |___  | |  
 |_|   |_| \\_\\\\___/ \\___/|_____\\____| |_|  
                                          
       D E C I D E X   P F I O S          
=========================================`}
        </pre>
      </div>

      {/* Main Authentication Terminal Box */}
      <div className="w-full max-w-md border border-zinc-800 bg-zinc-950 p-6 rounded-none relative">
        {/* Terminal Header */}
        <div className="flex justify-between items-center mb-6 pb-2 border-b border-zinc-900 text-xs text-zinc-400">
          <span>SECURE_SHELL://AUTHENTICATION</span>
          <span>v0.1.0</span>
        </div>

        {isLogin ? (
          <div>
            <h2 className="text-sm uppercase tracking-wider text-zinc-300 mb-4 font-bold">
              [SIGN_IN_REQUIRED]
            </h2>
            <p className="text-xs text-zinc-500 mb-6">
              Enter credentials to establish security context.
            </p>
          </div>
        ) : (
          <div>
            <h2 className="text-sm uppercase tracking-wider text-zinc-300 mb-4 font-bold">
              [CREATE_NEW_IDENTITY]
            </h2>
            <p className="text-xs text-zinc-500 mb-6">
              Register email and password to provision a personal portfolio.
            </p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-xs uppercase tracking-wider text-zinc-400 mb-2">
              Email Address:
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-black border border-zinc-800 text-white rounded-none py-2 px-3 focus:outline-none focus:border-white text-sm font-mono"
              placeholder="operator@domain.com"
              required
              disabled={loading}
            />
          </div>

          <div>
            <label className="block text-xs uppercase tracking-wider text-zinc-400 mb-2">
              Secret Key (Password):
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-black border border-zinc-800 text-white rounded-none py-2 px-3 focus:outline-none focus:border-white text-sm font-mono"
              placeholder="••••••••••••"
              required
              disabled={loading}
            />
          </div>

          {error && (
            <div className="border border-red-900 bg-red-950/20 text-red-500 p-3 rounded-none text-xs">
              <span className="font-bold">ERROR: </span>
              {error}
            </div>
          )}

          <div className="flex flex-col space-y-4">
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-white text-black py-2.5 rounded-none font-bold uppercase text-xs tracking-widest hover:bg-zinc-200 transition-colors duration-150 disabled:bg-zinc-800 disabled:text-zinc-500 cursor-pointer"
            >
              {loading ? "AUTHENTICATING..." : isLogin ? "EXECUTE LOGIN" : "EXECUTE SIGNUP"}
            </button>

            <button
              type="button"
              disabled={loading}
              onClick={() => {
                setIsLogin(!isLogin);
                setError(null);
              }}
              className="w-full bg-transparent text-zinc-400 py-2 rounded-none text-xs tracking-wider border border-transparent hover:border-zinc-800 hover:text-white transition-colors duration-150 cursor-pointer"
            >
              {isLogin ? "PROVISION NEW ACCESS [SIGN UP]" : "EXISTING ACCESS KEY [SIGN IN]"}
            </button>
          </div>
        </form>
      </div>

      {/* Footer message */}
      <div className="mt-8 text-center text-[10px] text-zinc-600 tracking-wider">
        <span>SECURITY PROTOCOL ENFORCED (3-DAY ROLLING CREDENTIALS)</span>
      </div>
    </div>
  );
}
