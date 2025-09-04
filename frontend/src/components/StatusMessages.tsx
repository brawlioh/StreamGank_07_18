import { useState, useEffect, useRef } from "react";

interface StatusMessage {
    id: string;
    type: "success" | "error" | "warning" | "info" | "waiting";
    icon: string;
    message: string;
    timestamp: number;
}

interface StatusMessagesProps {
    className?: string;
}

export default function StatusMessages({ className = "" }: StatusMessagesProps) {
    const [messages, setMessages] = useState<StatusMessage[]>([
        {
            id: "initial",
            type: "waiting",
            icon: "⏳",
            message: "Ready to generate video. Click the Generate button to start.",
            timestamp: Date.now(),
        },
    ]);
    const containerRef = useRef<HTMLDivElement>(null);

    const addMessage = (type: StatusMessage["type"], icon: string, message: string) => {
        const newMessage: StatusMessage = {
            id: `${Date.now()}-${Math.random()}`,
            type,
            icon,
            message,
            timestamp: Date.now(),
        };

        setMessages((prev) => [...prev, newMessage]);

        // Auto-scroll to bottom
        setTimeout(() => {
            if (containerRef.current) {
                containerRef.current.scrollTop = containerRef.current.scrollHeight;
            }
        }, 100);
    };

    const clearMessages = () => {
        setMessages([]);
    };

    // Listen for global status message events
    useEffect(() => {
        const handleAddMessage = (event: CustomEvent) => {
            const { type, icon, message } = event.detail;
            addMessage(type, icon, message);
        };

        const handleClearMessages = () => {
            clearMessages();
        };

        window.addEventListener("add-status-message", handleAddMessage as EventListener);
        window.addEventListener("clear-logs", handleClearMessages);

        return () => {
            window.removeEventListener("add-status-message", handleAddMessage as EventListener);
            window.removeEventListener("clear-logs", handleClearMessages);
        };
    }, []);

    const getMessageClass = (type: string) => {
        const baseClass = "status-message";
        return `${baseClass} ${type}`;
    };

    const formatTimestamp = (timestamp: number) => {
        return new Date(timestamp).toLocaleTimeString("en-US", {
            hour12: false,
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    };

    return (
        <div className={`status-messages ${className}`} id="status-messages" ref={containerRef}>
            {messages.map((message) => (
                <div key={message.id} className={getMessageClass(message.type)}>
                    <span className="status-icon">{message.icon}</span>
                    <span className="status-text">{message.message}</span>
                    <span className="text-xs ml-2 opacity-70">{formatTimestamp(message.timestamp)}</span>
                </div>
            ))}
        </div>
    );
}

// Global function to add status messages from anywhere in the app
export const addStatusMessage = (type: StatusMessage["type"], icon: string, message: string) => {
    window.dispatchEvent(
        new CustomEvent("add-status-message", {
            detail: { type, icon, message },
        })
    );
};
