"use client";

import { useState, useEffect, createContext, useContext, useCallback } from "react";

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
    id: string;
    type: ToastType;
    message: string;
}

interface ToastContextValue {
    addToast: (type: ToastType, message: string) => void;
}

const ToastContext = createContext<ToastContextValue>({ addToast: () => { } });

export function useToast() {
    return useContext(ToastContext);
}

const toastStyles: Record<ToastType, { bg: string; border: string; icon: string }> = {
    success: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", icon: "✅" },
    error: { bg: "bg-rose-500/10", border: "border-rose-500/20", icon: "❌" },
    info: { bg: "bg-sky-500/10", border: "border-sky-500/20", icon: "ℹ️" },
    warning: { bg: "bg-amber-500/10", border: "border-amber-500/20", icon: "⚠️" },
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const addToast = useCallback((type: ToastType, message: string) => {
        const id = Math.random().toString(36).slice(2);
        setToasts((prev) => [...prev, { id, type, message }]);
    }, []);

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    return (
        <ToastContext.Provider value={{ addToast }}>
            {children}
            {/* Toast Container */}
            <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
                {toasts.map((toast) => (
                    <ToastItem key={toast.id} toast={toast} onDismiss={removeToast} />
                ))}
            </div>
        </ToastContext.Provider>
    );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
    const s = toastStyles[toast.type];

    useEffect(() => {
        const timer = setTimeout(() => onDismiss(toast.id), 4000);
        return () => clearTimeout(timer);
    }, [toast.id, onDismiss]);

    return (
        <div
            className={`
        ${s.bg} border ${s.border} backdrop-blur-xl rounded-xl
        px-4 py-3 flex items-center gap-3 animate-slideIn cursor-pointer
        hover:opacity-80 transition-opacity
      `}
            onClick={() => onDismiss(toast.id)}
        >
            <span className="text-lg">{s.icon}</span>
            <p className="text-sm text-slate-200 flex-1">{toast.message}</p>
        </div>
    );
}
