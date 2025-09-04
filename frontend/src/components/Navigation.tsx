import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";

interface NavigationProps {
    queueCount?: number;
    connectionStatus?: "connected" | "disconnected" | "warning";
    onRefresh?: () => void;
}

export default function Navigation({ queueCount = 0, connectionStatus = "connected", onRefresh }: NavigationProps) {
    const location = useLocation();
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);

    const navigationLinks = [
        {
            path: "/dashboard",
            label: "Dashboard",
            icon: "fas fa-home",
            description: "Main Dashboard",
        },
        {
            path: "/queue",
            label: "Queue",
            icon: "fas fa-tasks",
            description: "Queue Management",
        },
    ];

    const isActiveRoute = (path: string): boolean => {
        if (location.pathname === path) return true;
        if (path === "/dashboard" && location.pathname === "/") return true;
        if (path === "/queue" && location.pathname.startsWith("/job/")) return true;
        return false;
    };

    const getStatusDotClass = () => {
        switch (connectionStatus) {
            case "connected":
                return "status-dot bg-success";
            case "warning":
                return "status-dot bg-warning";
            case "disconnected":
                return "status-dot bg-danger";
            default:
                return "status-dot bg-success";
        }
    };

    const getQueueCounterClass = () => {
        if (queueCount === 0) return "queue-counter bg-secondary hidden";
        if (queueCount > 5) return "queue-counter bg-danger";
        return "queue-counter bg-warning";
    };

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            const dropdown = document.getElementById("settings-dropdown");
            if (dropdown && !dropdown.contains(event.target as Node)) {
                setIsDropdownOpen(false);
            }
        };

        if (isDropdownOpen) {
            document.addEventListener("click", handleClickOutside);
        }

        return () => {
            document.removeEventListener("click", handleClickOutside);
        };
    }, [isDropdownOpen]);

    return (
        <header className="streamgank-header">
            <div className="container-fluid">
                <div className="flex py-2 items-center">
                    <div className="flex-1">
                        <Link to="/dashboard" className="flex items-center" style={{ textDecoration: "none", color: "inherit" }}>
                            <h1 className="logo mb-0 mr-2">
                                Stream
                                <span className="text-gank">Gank</span>
                            </h1>
                            <span className="version-tag ml-2">BETA v1.3</span>
                        </Link>
                        <span className="tagline block">AMBUSH THE BEST VOD TOGETHER</span>
                    </div>

                    <div className="flex items-center gap-3">
                        {/* Main Navigation */}
                        <nav className="flex gap-2">
                            {navigationLinks.map((link) => {
                                const isActive = isActiveRoute(link.path);
                                return (
                                    <Link key={link.path} to={link.path} className={`professional-nav-link btn btn-sm ${isActive ? "active" : "inactive"}`} title={link.description}>
                                        <i className={`${link.icon} mr-2 text-sm`}></i>
                                        <span className="nav-text">{link.label}</span>
                                        {link.path === "/queue" && queueCount > 0 && <span className={`${getQueueCounterClass()} ml-2`}>{queueCount}</span>}
                                    </Link>
                                );
                            })}
                        </nav>

                        {/* Connection Status */}
                        <div className="connection-status">
                            <div className={getStatusDotClass()} title={`Connection: ${connectionStatus}`}></div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-2">
                            <button onClick={onRefresh} className="btn btn-outline-light btn-sm" title="Refresh Data">
                                <i className="fas fa-sync-alt"></i>
                            </button>

                            {/* Settings Dropdown */}
                            <div className="relative" id="settings-dropdown">
                                <button onClick={() => setIsDropdownOpen(!isDropdownOpen)} className="btn btn-outline-light btn-sm" title="Settings">
                                    <i className="fas fa-cog"></i>
                                </button>

                                {isDropdownOpen && (
                                    <div className="absolute right-0 mt-2 w-48 bg-dark-panel border border-border-color rounded-md shadow-lg z-50">
                                        <div className="py-1">
                                            <button
                                                onClick={() => {
                                                    // Toggle queue dashboard functionality
                                                    setIsDropdownOpen(false);
                                                }}
                                                className="block w-full text-left px-4 py-2 text-sm text-text-light hover:bg-white/10"
                                            >
                                                Queue Dashboard
                                            </button>
                                            <button
                                                onClick={() => {
                                                    // Clear logs functionality
                                                    if (confirm("Clear all status messages?")) {
                                                        // Emit event for clearing logs
                                                        window.dispatchEvent(new CustomEvent("clear-logs"));
                                                    }
                                                    setIsDropdownOpen(false);
                                                }}
                                                className="block w-full text-left px-4 py-2 text-sm text-text-light hover:bg-white/10"
                                            >
                                                Clear Logs
                                            </button>
                                            <hr className="my-1 border-border-color" />
                                            <button
                                                onClick={() => {
                                                    alert("App Status: OK\nConnection: Active\nBuild: Production");
                                                    setIsDropdownOpen(false);
                                                }}
                                                className="block w-full text-left px-4 py-2 text-sm text-text-light hover:bg-white/10"
                                            >
                                                App Status
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <button className="btn btn-primary btn-sm">
                                <i className="fas fa-sign-in-alt mr-1"></i>
                                LOGIN
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </header>
    );
}
