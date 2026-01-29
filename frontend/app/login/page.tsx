"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Link from "next/link";

export default function LoginPage() {
    const { login, register } = useAuth();
    const [isLogin, setIsLogin] = useState(true);

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [name, setName] = useState("");
    const [yearGroup, setYearGroup] = useState(5);
    const [error, setError] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        try {
            if (isLogin) {
                await login(email, password);
            } else {
                await register(email, password, name, yearGroup);
            }
        } catch (err: any) {
            console.error(err);
            setError(err.message || "Authentication failed. Check your credentials.");
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-2xl shadow-xl">
                <div>
                    <div className="mx-auto h-12 w-12 bg-indigo-100 rounded-full flex items-center justify-center text-2xl">
                        DT
                    </div>
                    <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
                        {isLogin ? "Sign in to DeepTutor" : "Create your account"}
                    </h2>
                    <p className="mt-2 text-center text-sm text-gray-600">
                        {isLogin ? "Or" : "Already have an account?"}{" "}
                        <button
                            onClick={() => setIsLogin(!isLogin)}
                            className="font-medium text-indigo-600 hover:text-indigo-500"
                        >
                            {isLogin ? "create a new account" : "sign in instead"}
                        </button>
                    </p>
                </div>

                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm">
                        {error}
                    </div>
                )}

                <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
                    <div className="rounded-md shadow-sm space-y-4">
                        {!isLogin && (
                            <>
                                <div>
                                    <label className="sr-only">Full Name</label>
                                    <input
                                        type="text"
                                        required
                                        className="appearance-none rounded-lg relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                                        placeholder="Full Name"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                    />
                                </div>
                                <div>
                                    <label className="text-sm text-gray-700 ml-1">Year Group (Target)</label>
                                    <select
                                        value={yearGroup}
                                        onChange={(e) => setYearGroup(Number(e.target.value))}
                                        className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-lg"
                                    >
                                        <option value={4}>Year 4</option>
                                        <option value={5}>Year 5</option>
                                        <option value={6}>Year 6</option>
                                    </select>
                                </div>
                            </>
                        )}

                        <div>
                            <label className="sr-only">Email address</label>
                            <input
                                type="email"
                                required
                                className="appearance-none rounded-lg relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                                placeholder="Email address"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="sr-only">Password</label>
                            <input
                                type="password"
                                required
                                className="appearance-none rounded-lg relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                                placeholder="Password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                            />
                        </div>
                    </div>

                    <div>
                        <button
                            type="submit"
                            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                        >
                            {isLogin ? "Sign in" : "Register"}
                        </button>
                    </div>
                </form>

                <div className="text-center mt-4">
                    <Link href="/" className="text-sm text-gray-500 hover:text-gray-900">Back to Dashboard</Link>
                </div>
            </div>
        </div>
    );
}
