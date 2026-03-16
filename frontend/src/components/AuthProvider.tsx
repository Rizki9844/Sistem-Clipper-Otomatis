"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { useRouter, usePathname } from "next/navigation";
import { getToken, setToken, removeToken } from "@/lib/auth";
import {
  login as apiLogin,
  register as apiRegister,
  getMe,
  type UserProfile,
  type LoginRequest,
  type RegisterRequest,
} from "@/lib/api/auth";

interface AuthContextType {
  user: UserProfile | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const PUBLIC_PATHS = ["/login"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  // On mount: check stored token & fetch profile
  useEffect(() => {
    async function init() {
      const token = getToken();
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const profile = await getMe();
        setUser(profile);
      } catch {
        // Token invalid/expired — clear it
        removeToken();
      } finally {
        setIsLoading(false);
      }
    }
    init();
  }, []);

  // Redirect unauthenticated users to /login
  useEffect(() => {
    if (isLoading) return;
    if (!user && !PUBLIC_PATHS.includes(pathname)) {
      router.replace("/login");
    }
  }, [user, isLoading, pathname, router]);

  const login = useCallback(async (data: LoginRequest) => {
    const tokenRes = await apiLogin(data);
    setToken(tokenRes.access_token);
    const profile = await getMe();
    setUser(profile);
    router.push("/");
  }, [router]);

  const register = useCallback(async (data: RegisterRequest) => {
    await apiRegister(data);
    // Auto-login after registration
    const tokenRes = await apiLogin({
      email: data.email,
      password: data.password,
    });
    setToken(tokenRes.access_token);
    const profile = await getMe();
    setUser(profile);
    router.push("/");
  }, [router]);

  const logout = useCallback(() => {
    removeToken();
    setUser(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
