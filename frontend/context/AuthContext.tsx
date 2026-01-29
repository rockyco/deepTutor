"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { User, authAPI } from "@/lib/api";
import { useRouter } from "next/navigation";

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<void>;
    register: (email: string, password: string, name: string, yearGroup: number) => Promise<void>;
    logout: () => void;
    updateLocalUser: (updates: Partial<User>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        checkUser();
    }, []);

    async function checkUser() {
        try {
            if (localStorage.getItem("token")) {
                const userData = await authAPI.getMe();
                setUser(userData);
            }
        } catch (err) {
            console.error("Auth check failed", err);
            localStorage.removeItem("token");
        } finally {
            setLoading(false);
        }
    }

    const login = async (email: string, password: string) => {
        const { access_token } = await authAPI.login(email, password);
        localStorage.setItem("token", access_token);
        await checkUser();
        router.push("/");
    };

    const register = async (email: string, password: string, name: string, yearGroup: number) => {
        const { access_token } = await authAPI.register(email, password, name, yearGroup);
        console.log("Registered token:", access_token);
        localStorage.setItem("token", access_token);
        await checkUser();
        router.push("/");
    };

    const logout = () => {
        localStorage.removeItem("token");
        setUser(null);
        router.push("/login");
    };

    const updateLocalUser = (updates: Partial<User>) => {
        if (user) {
            setUser({ ...user, ...updates });
        }
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout, updateLocalUser }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
