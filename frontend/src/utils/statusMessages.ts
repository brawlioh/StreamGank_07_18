export type StatusMessageType = "success" | "error" | "warning" | "info" | "waiting";

// Global function to add status messages from anywhere in the app
export const addStatusMessage = (type: StatusMessageType, icon: string, message: string) => {
    window.dispatchEvent(
        new CustomEvent("add-status-message", {
            detail: { type, icon, message },
        })
    );
};
