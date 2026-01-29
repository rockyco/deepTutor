"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "@/components/Sidebar";
import { useAuth } from "@/context/AuthContext";
import { authAPI } from "@/lib/api";

export default function SettingsPage() {
    const { user, updateLocalUser, logout } = useAuth();
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState("");

    const [aiProvider, setAiProvider] = useState("auto");
    const [modelName, setModelName] = useState("");
    const [apiKey, setApiKey] = useState("");

    useEffect(() => {
        if (user?.ai_settings) {
            setAiProvider(user.ai_settings.ai_provider || "auto");
            setModelName(user.ai_settings.model_name || "");
            // API key is usually not sent back for security, or masked
        }
    }, [user]);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setSuccess("");
        try {
            const settings = {
                ai_provider: aiProvider,
                model_name: modelName || undefined,
                api_key: apiKey || undefined,
            };

            await authAPI.updateSettings(settings);

            // Update local context
            updateLocalUser({
                ai_settings: {
                    ...user?.ai_settings,
                    ...settings
                }
            });

            setSuccess("Settings saved successfully!");
            setApiKey(""); // Clear sensitive field
        } catch (err) {
            console.error(err);
            alert("Failed to save settings.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex h-screen bg-slate-50/50">
            <Sidebar />
            <main className="flex-grow p-8 overflow-y-auto">
                <header className="mb-8">
                    <h1 className="text-2xl font-bold text-slate-900">Settings & Configuration</h1>
                    <p className="text-slate-500">Manage your profile and AI preferences.</p>
                </header>

                <div className="max-w-3xl space-y-6">
                    {/* User Profile Card */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
                        <h2 className="text-lg font-bold text-slate-800 mb-4">User Profile</h2>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <label className="block text-slate-500 mb-1">Name</label>
                                <div className="font-medium text-slate-900">{user?.name || "Guest"}</div>
                            </div>
                            <div>
                                <label className="block text-slate-500 mb-1">Email</label>
                                <div className="font-medium text-slate-900">{user?.id ? (user as any).email : "Not Logged In"}</div>
                            </div>
                            <div>
                                <label className="block text-slate-500 mb-1">Year Group</label>
                                <div className="font-medium text-slate-900">Year {user?.year_group || 5}</div>
                            </div>
                        </div>

                        <button
                            onClick={logout}
                            className="mt-6 px-4 py-2 border border-red-200 text-red-600 rounded-lg hover:bg-red-50 text-sm font-medium"
                        >
                            Sign Out
                        </button>
                    </div>

                    {/* AI Settings Card */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
                        <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
                            <span>🤖</span> AI Model Configuration
                        </h2>
                        <p className="text-sm text-slate-500 mb-6">
                            Customize which AI model drives your tuition. "Auto" uses the system default (Hybrid Vertex/Gemini).
                        </p>

                        <form onSubmit={handleSave} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">AI Provider</label>
                                <select
                                    value={aiProvider}
                                    onChange={(e) => setAiProvider(e.target.value)}
                                    className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                                >
                                    <option value="auto">Auto (Recommended)</option>
                                    <option value="gemini">Google Gemini (API Key)</option>
                                    <option value="vertex">Google Vertex AI (Cloud Identity)</option>
                                    <option value="openai">OpenAI (GPT-4)</option>
                                    <option value="anthropic">Anthropic (Claude 3.5)</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Model Name (Optional)</label>
                                <input
                                    type="text"
                                    value={modelName}
                                    onChange={(e) => setModelName(e.target.value)}
                                    placeholder="e.g. gemini-2.0-flash, gpt-4-turbo"
                                    className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                                />
                                <p className="mt-1 text-xs text-gray-500">Leave blank to use provider default.</p>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">API Key (Optional)</label>
                                <input
                                    type="password"
                                    value={apiKey}
                                    onChange={(e) => setApiKey(e.target.value)}
                                    placeholder="sk-..."
                                    className="w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                                />
                                <p className="mt-1 text-xs text-gray-500">Only needed if overriding the default system key.</p>
                            </div>

                            {success && (
                                <div className="p-3 bg-green-50 text-green-700 rounded-lg text-sm">
                                    {success}
                                </div>
                            )}

                            <div className="pt-4">
                                <button
                                    type="submit"
                                    disabled={loading || !user}
                                    className={cn(
                                        "px-6 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition shadow-sm",
                                        (loading || !user) && "opacity-50 cursor-not-allowed"
                                    )}
                                >
                                    {loading ? "Saving..." : "Save Preferences"}
                                </button>
                                {!user && <p className="text-xs text-red-500 mt-2">You must be logged in to save settings.</p>}
                            </div>
                        </form>
                    </div>
                </div>
            </main>
        </div>
    );
}

function cn(...classes: (string | undefined | null | false)[]) {
    return classes.filter(Boolean).join(" ");
}
