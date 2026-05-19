import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

const HEALTH_INTERVAL = 10_000;
const ACCEPTED_TYPES = ["audio/mp3"];
const MAX_SIZE = 25 * 1024 * 1024;

function formatBytes(bytes) {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / k ** i).toFixed(1)} ${sizes[i]}`;
}

function formatDuration(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
}

const spring = { type: "spring", stiffness: 350, damping: 28 };
const springGentle = { type: "spring", stiffness: 180, damping: 22 };
const springSnappy = { type: "spring", stiffness: 500, damping: 30 };

const cardVariants = {
    hidden: { opacity: 0, y: 20, scale: 0.98, filter: "blur(4px)" },
    visible: {
        opacity: 1,
        y: 0,
        scale: 1,
        filter: "blur(0px)",
        transition: { ...springGentle, staggerChildren: 0.07 },
    },
    exit: {
        opacity: 0,
        y: -12,
        scale: 0.98,
        filter: "blur(4px)",
        transition: { duration: 0.18, ease: "easeIn" },
    },
};

const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: springGentle },
};

function StatusBadge() {
    const [status, setStatus] = useState({
        online: false,
        model: false,
        checking: true,
    });

    useEffect(() => {
        let mounted = true;
        async function check() {
            try {
                const res = await fetch("/api/health-check");
                if (!mounted) return;
                if (res.ok) {
                    const data = await res.json();
                    setStatus({
                        online: true,
                        model: data.model_loaded ?? false,
                        checking: false,
                    });
                } else {
                    setStatus({ online: true, model: false, checking: false });
                }
            } catch {
                if (mounted)
                    setStatus({ online: false, model: false, checking: false });
            }
        }
        check();
        const id = setInterval(check, HEALTH_INTERVAL);
        return () => {
            mounted = false;
            clearInterval(id);
        };
    }, []);

    const dotColor = status.checking
        ? "bg-text-muted"
        : !status.online
          ? "bg-error"
          : status.model
            ? "bg-success"
            : "bg-cyan";

    const textColor = status.checking
        ? "text-text-muted"
        : !status.online
          ? "text-error"
          : status.model
            ? "text-success"
            : "text-cyan";

    const label = status.checking
        ? "Connecting"
        : !status.online
          ? "Offline"
          : status.model
            ? "Model Ready"
            : "No Model";

    return (
        <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4, ...springGentle }}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${textColor} text-[11px] font-mono tracking-wide`}
            style={{
                background: "rgba(20, 18, 30, 0.6)",
                border: "1px solid rgba(140, 80, 255, 0.08)",
            }}
        >
            <span className="relative flex h-1.5 w-1.5">
                {status.model && !status.checking && (
                    <motion.span
                        className="absolute inline-flex h-full w-full rounded-full bg-success"
                        animate={{ scale: [1, 1.8, 1], opacity: [0.7, 0, 0.7] }}
                        transition={{ duration: 2, repeat: Infinity }}
                    />
                )}
                <motion.span
                    className={`relative inline-flex rounded-full h-1.5 w-1.5 ${dotColor}`}
                    animate={
                        status.checking
                            ? { opacity: [0.3, 1, 0.3] }
                            : undefined
                    }
                    transition={
                        status.checking
                            ? { duration: 1.2, repeat: Infinity }
                            : undefined
                    }
                />
            </span>
            {label}
        </motion.div>
    );
}

function WaveformVisualizer({ active, barCount = 48 }) {
    return (
        <div className="flex items-end justify-center gap-[1.5px] h-16 px-1">
            {Array.from({ length: barCount }, (_, i) => {
                const center = Math.abs(i - barCount / 2) / (barCount / 2);
                const baseHeight = active
                    ? 12 + (1 - center) * 88
                    : 6 + (1 - center) * 28;
                const delay = i * 0.03;
                return (
                    <motion.div
                        key={i}
                        className="w-[2px] rounded-full origin-bottom"
                        initial={{ scaleY: 0, opacity: 0 }}
                        animate={{ scaleY: 1, opacity: 1 }}
                        transition={{ delay: delay * 0.4, ...spring }}
                        style={{
                            height: `${baseHeight}%`,
                            background: active
                                ? `linear-gradient(to top, var(--color-accent) 0%, var(--color-cyan) 100%)`
                                : `linear-gradient(to top, var(--color-accent-light) 0%, var(--color-accent-bright) 100%)`,
                            animation: active
                                ? `wave-bar 0.6s ease-in-out ${delay}s infinite`
                                : "none",
                            opacity: active ? 0.85 : 0.15,
                        }}
                    />
                );
            })}
        </div>
    );
}

function AmbientBackground() {
    return (
        <div className="fixed inset-0 -z-10 overflow-hidden">
            <div
                className="absolute inset-0"
                style={{ background: "var(--color-void)" }}
            />
            <div
                className="absolute inset-0 opacity-[0.035]"
                style={{
                    backgroundImage:
                        "radial-gradient(circle, rgba(140,80,255,0.8) 1px, transparent 1px)",
                    backgroundSize: "32px 32px",
                }}
            />
            <motion.div
                className="absolute rounded-full"
                style={{
                    width: 700,
                    height: 700,
                    background:
                        "radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 65%)",
                    top: "-15%",
                    left: "25%",
                }}
                animate={{ x: [0, 50, -30, 0], y: [0, -40, 25, 0] }}
                transition={{
                    duration: 24,
                    repeat: Infinity,
                    ease: "easeInOut",
                }}
            />
            <motion.div
                className="absolute rounded-full"
                style={{
                    width: 500,
                    height: 500,
                    background:
                        "radial-gradient(circle, rgba(34,211,238,0.035) 0%, transparent 65%)",
                    bottom: "-8%",
                    right: "5%",
                }}
                animate={{ x: [0, -35, 25, 0], y: [0, 25, -35, 0] }}
                transition={{
                    duration: 28,
                    repeat: Infinity,
                    ease: "easeInOut",
                }}
            />
            <div
                className="absolute inset-0 opacity-[0.012]"
                style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
                    backgroundRepeat: "repeat",
                }}
            />
        </div>
    );
}

function SonicRings({ active }) {
    if (!active) return null;
    return (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            {[0, 1, 2].map((i) => (
                <motion.div
                    key={i}
                    className="absolute rounded-full border"
                    style={{
                        width: 80,
                        height: 80,
                        borderColor: "rgba(139,92,246,0.15)",
                    }}
                    animate={{ scale: [0.8, 2.2], opacity: [0.5, 0] }}
                    transition={{
                        duration: 2.4,
                        repeat: Infinity,
                        delay: i * 0.8,
                        ease: "easeOut",
                    }}
                />
            ))}
        </div>
    );
}

function OrbitalProgress() {
    return (
        <div className="relative w-20 h-20 mx-auto">
            <div
                className="absolute inset-0 rounded-full"
                style={{ border: "1.5px solid rgba(139,92,246,0.1)" }}
            />
            <motion.div
                className="absolute inset-0"
                animate={{ rotate: 360 }}
                transition={{ duration: 1.8, repeat: Infinity, ease: "linear" }}
            >
                <svg viewBox="0 0 80 80" className="w-full h-full" fill="none">
                    <circle
                        cx="40"
                        cy="40"
                        r="39"
                        stroke="url(#orbital-grad)"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeDasharray="60 185"
                    />
                    <defs>
                        <linearGradient
                            id="orbital-grad"
                            x1="0"
                            y1="0"
                            x2="80"
                            y2="80"
                        >
                            <stop offset="0%" stopColor="var(--color-accent)" />
                            <stop
                                offset="100%"
                                stopColor="var(--color-cyan)"
                            />
                        </linearGradient>
                    </defs>
                </svg>
            </motion.div>
            <motion.div
                className="absolute inset-0"
                animate={{ rotate: 360 }}
                transition={{ duration: 1.8, repeat: Infinity, ease: "linear" }}
            >
                <div
                    className="absolute w-2 h-2 rounded-full"
                    style={{
                        background: "var(--color-cyan)",
                        boxShadow: "0 0 8px var(--color-cyan)",
                        top: 0,
                        left: "50%",
                        transform: "translate(-50%, -1px)",
                    }}
                />
            </motion.div>
        </div>
    );
}

function UploadZone({ onFile, dragOver, setDragOver, inputRef }) {
    return (
        <motion.div
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="relative cursor-pointer"
            onClick={() => inputRef.current?.click()}
            onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                const f = e.dataTransfer?.files?.[0];
                if (f) onFile(f);
            }}
            onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
            }}
            onDragLeave={(e) => {
                e.preventDefault();
                setDragOver(false);
            }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ")
                    inputRef.current?.click();
            }}
        >
            <motion.div
                className="relative rounded-2xl overflow-hidden"
                animate={{
                    borderColor: dragOver
                        ? "rgba(139,92,246,0.5)"
                        : "rgba(139,92,246,0.12)",
                }}
                whileHover={{ borderColor: "rgba(139,92,246,0.25)" }}
                transition={{ duration: 0.2 }}
                style={{
                    border: "1px solid rgba(139,92,246,0.12)",
                    background: dragOver
                        ? "rgba(139,92,246,0.04)"
                        : "rgba(12,11,18,0.7)",
                    boxShadow: dragOver
                        ? "0 0 80px rgba(139,92,246,0.1), inset 0 1px 0 rgba(255,255,255,0.04)"
                        : "0 8px 40px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.03)",
                }}
            >
                <div
                    className="absolute top-0 left-[10%] right-[10%] h-[1px]"
                    style={{
                        background:
                            "linear-gradient(90deg, transparent, rgba(139,92,246,0.2), transparent)",
                    }}
                />

                <div className="px-8 py-16 flex flex-col items-center text-center relative">
                    <input
                        ref={inputRef}
                        type="file"
                        accept=".mp3"
                        className="hidden"
                        onChange={(e) => {
                            const f = e.target.files?.[0];
                            if (f) onFile(f);
                            e.target.value = "";
                        }}
                    />

                    <SonicRings active={dragOver} />

                    <motion.div variants={itemVariants} className="mb-8 relative">
                        <motion.div
                            className="w-20 h-20 rounded-full flex items-center justify-center relative"
                            style={{
                                background:
                                    "radial-gradient(circle, rgba(139,92,246,0.08) 0%, transparent 70%)",
                                border: "1px solid rgba(139,92,246,0.12)",
                            }}
                            whileHover={{ scale: 1.06 }}
                            transition={spring}
                        >
                            <svg
                                width="28"
                                height="28"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="var(--color-accent-light)"
                                strokeWidth="1.5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                            >
                                <path d="M12 16V4M12 4L7 9M12 4L17 9" />
                            </svg>
                        </motion.div>
                    </motion.div>

                    <motion.h2
                        variants={itemVariants}
                        className="text-text text-[17px] font-semibold mb-2 tracking-[-0.01em]"
                    >
                        Upload MP3 to reconstruct
                    </motion.h2>
                    <motion.p
                        variants={itemVariants}
                        className="text-text-muted text-sm mb-6"
                    >
                        Drag and drop or click to browse
                    </motion.p>

                    <motion.div
                        variants={itemVariants}
                        className="flex items-center gap-2.5"
                    >
                        <span
                            className="px-3 py-1.5 rounded-lg text-[11px] font-mono font-medium tracking-wider text-accent-light"
                            style={{
                                background: "rgba(139,92,246,0.06)",
                                border: "1px solid rgba(139,92,246,0.1)",
                            }}
                        >
                            .MP3
                        </span>
                        <span className="text-text-muted/40 text-xs">
                            &bull;
                        </span>
                        <span className="text-text-muted text-[11px] font-mono">
                            {formatBytes(MAX_SIZE)} limit
                        </span>
                    </motion.div>
                </div>
            </motion.div>
        </motion.div>
    );
}

function ReadyCard({ file, onReconstruct, onReset }) {
    return (
        <motion.div
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="rounded-2xl overflow-hidden"
            style={{
                background: "rgba(12,11,18,0.75)",
                border: "1px solid rgba(139,92,246,0.12)",
                boxShadow:
                    "0 8px 40px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.03)",
            }}
        >
            <div
                className="h-[1px]"
                style={{
                    background:
                        "linear-gradient(90deg, transparent, rgba(139,92,246,0.2), transparent)",
                }}
            />
            <div className="p-6 space-y-5">
                <motion.div
                    variants={itemVariants}
                    className="flex items-center gap-3.5"
                >
                    <div
                        className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0"
                        style={{
                            background: "rgba(139,92,246,0.06)",
                            border: "1px solid rgba(139,92,246,0.1)",
                        }}
                    >
                        <svg
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="var(--color-accent-light)"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                        >
                            <path d="M9 18V5l12-2v13" />
                            <circle cx="6" cy="18" r="3" />
                            <circle cx="18" cy="16" r="3" />
                        </svg>
                    </div>
                    <div className="min-w-0 flex-1">
                        <p className="text-text text-[14px] font-medium truncate leading-tight">
                            {file.name}
                        </p>
                        <p className="text-text-muted text-[11px] mt-1 font-mono tracking-wide">
                            {formatBytes(file.size)}
                        </p>
                    </div>
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        transition={springSnappy}
                        onClick={onReset}
                        className="text-text-muted hover:text-error transition-colors p-2 rounded-lg cursor-pointer"
                        style={{ background: "transparent" }}
                        aria-label="Remove file"
                    >
                        <svg
                            width="14"
                            height="14"
                            viewBox="0 0 14 14"
                            fill="none"
                        >
                            <path
                                d="M3 3L11 11M11 3L3 11"
                                stroke="currentColor"
                                strokeWidth="1.5"
                                strokeLinecap="round"
                            />
                        </svg>
                    </motion.button>
                </motion.div>

                <motion.div variants={itemVariants}>
                    <WaveformVisualizer active={false} />
                </motion.div>

                <motion.div variants={itemVariants}>
                    <motion.button
                        whileHover={{ y: -1 }}
                        whileTap={{ scale: 0.985 }}
                        transition={spring}
                        onClick={onReconstruct}
                        className="w-full flex items-center justify-center gap-2.5 py-3.5 text-white font-medium text-[14px] rounded-xl cursor-pointer border-0 tracking-[-0.01em]"
                        style={{
                            background:
                                "linear-gradient(135deg, var(--color-accent) 0%, #7c3aed 100%)",
                            boxShadow:
                                "0 0 24px rgba(139,92,246,0.2), 0 2px 8px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)",
                        }}
                    >
                        <svg
                            width="15"
                            height="15"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <path d="M12 2L2 7l10 5 10-5-10-5z" />
                            <path d="M2 17l10 5 10-5" />
                            <path d="M2 12l10 5 10-5" />
                        </svg>
                        Reconstruct
                    </motion.button>
                </motion.div>
            </div>
        </motion.div>
    );
}

function ProcessingCard({ file, elapsed }) {
    return (
        <motion.div
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="rounded-2xl overflow-hidden"
            style={{
                background: "rgba(12,11,18,0.8)",
                border: "1px solid rgba(139,92,246,0.18)",
                boxShadow:
                    "0 0 80px rgba(139,92,246,0.08), 0 8px 40px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.03)",
            }}
        >
            <div
                className="h-[1px]"
                style={{
                    background:
                        "linear-gradient(90deg, transparent, rgba(139,92,246,0.3), transparent)",
                }}
            />
            <div className="p-8 space-y-7">
                <motion.div variants={itemVariants}>
                    <OrbitalProgress />
                </motion.div>

                <motion.div
                    variants={itemVariants}
                    className="text-center space-y-1"
                >
                    <p className="text-accent-bright text-3xl font-mono font-semibold tracking-tighter">
                        {formatDuration(elapsed)}
                    </p>
                    <p className="text-text-secondary text-sm">
                        Reconstructing audio
                    </p>
                </motion.div>

                <motion.div variants={itemVariants}>
                    <WaveformVisualizer active={true} barCount={56} />
                </motion.div>

                <motion.p
                    variants={itemVariants}
                    className="text-text-muted text-[11px] text-center font-mono truncate tracking-wide"
                >
                    {file?.name}
                </motion.p>
            </div>
        </motion.div>
    );
}

function DoneCard({ result, elapsed, onDownload, onReset }) {
    return (
        <motion.div
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="rounded-2xl overflow-hidden"
            style={{
                background: "rgba(12,11,18,0.75)",
                border: "1px solid rgba(139,92,246,0.12)",
                boxShadow:
                    "0 8px 40px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.03)",
            }}
        >
            <div
                className="h-[1px]"
                style={{
                    background:
                        "linear-gradient(90deg, transparent, rgba(52,211,153,0.3), transparent)",
                }}
            />
            <div className="p-6 space-y-5">
                <motion.div
                    variants={itemVariants}
                    className="flex items-center gap-3"
                >
                    <motion.div
                        className="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
                        style={{
                            background: "rgba(52,211,153,0.08)",
                            border: "1px solid rgba(52,211,153,0.15)",
                        }}
                        initial={{ scale: 0, rotate: -90 }}
                        animate={{ scale: 1, rotate: 0 }}
                        transition={{
                            type: "spring",
                            stiffness: 400,
                            damping: 18,
                            delay: 0.15,
                        }}
                    >
                        <motion.svg
                            width="18"
                            height="18"
                            viewBox="0 0 18 18"
                            fill="none"
                        >
                            <motion.path
                                d="M4 9L7.5 12.5L14 5.5"
                                stroke="var(--color-success)"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                initial={{ pathLength: 0 }}
                                animate={{ pathLength: 1 }}
                                transition={{
                                    delay: 0.35,
                                    duration: 0.35,
                                    ease: "easeOut",
                                }}
                            />
                        </motion.svg>
                    </motion.div>
                    <div>
                        <p className="text-success text-[14px] font-medium">
                            Reconstruction complete
                        </p>
                        <p className="text-text-muted text-[11px] mt-0.5 font-mono tracking-wide">
                            {formatDuration(elapsed)} elapsed
                        </p>
                    </div>
                </motion.div>

                <motion.div
                    variants={itemVariants}
                    className="rounded-xl p-4 space-y-3"
                    style={{
                        background: "rgba(20, 18, 30, 0.5)",
                        border: "1px solid rgba(140, 80, 255, 0.06)",
                    }}
                >
                    {[
                        ["Output", result.name],
                        ["Size", formatBytes(result.size)],
                        ["Format", "FLAC — lossless"],
                    ].map(([label, value]) => (
                        <div
                            key={label}
                            className="flex items-center justify-between"
                        >
                            <span className="text-text-muted text-[11px] font-mono uppercase tracking-wider">
                                {label}
                            </span>
                            <span className="text-text-secondary text-[12px] font-mono truncate ml-4 max-w-[220px]">
                                {value}
                            </span>
                        </div>
                    ))}
                </motion.div>

                <motion.div variants={itemVariants} className="flex gap-2.5">
                    <motion.button
                        whileHover={{ y: -1 }}
                        whileTap={{ scale: 0.985 }}
                        transition={spring}
                        onClick={onDownload}
                        className="flex-1 flex items-center justify-center gap-2 py-3.5 text-white font-medium text-[14px] rounded-xl cursor-pointer border-0"
                        style={{
                            background:
                                "linear-gradient(135deg, var(--color-accent) 0%, #7c3aed 100%)",
                            boxShadow:
                                "0 0 24px rgba(139,92,246,0.2), 0 2px 8px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)",
                        }}
                    >
                        <svg
                            width="15"
                            height="15"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <path d="M12 3v12M12 15l-4-4M12 15l4-4" />
                            <path d="M4 15v4a1 1 0 001 1h14a1 1 0 001-1v-4" />
                        </svg>
                        Download FLAC
                    </motion.button>
                    <motion.button
                        whileHover={{ scale: 1.06 }}
                        whileTap={{ scale: 0.94 }}
                        transition={springSnappy}
                        onClick={onReset}
                        className="w-12 h-12 rounded-xl flex items-center justify-center cursor-pointer text-text-muted hover:text-accent-light transition-colors"
                        style={{
                            background: "transparent",
                            border: "1px solid rgba(139,92,246,0.12)",
                        }}
                    >
                        <svg
                            width="15"
                            height="15"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                        >
                            <path d="M4 12a8 8 0 0114.93-4M20 12a8 8 0 01-14.93 4" />
                            <path d="M16 4h4v4" />
                            <path d="M8 20H4v-4" />
                        </svg>
                    </motion.button>
                </motion.div>
            </div>
        </motion.div>
    );
}

export default function App() {
    const [phase, setPhase] = useState("idle");
    const [file, setFile] = useState(null);
    const [error, setError] = useState(null);
    const [result, setResult] = useState(null);
    const [elapsed, setElapsed] = useState(0);
    const [dragOver, setDragOver] = useState(false);
    const inputRef = useRef(null);
    const timerRef = useRef(null);

    const reset = useCallback(() => {
        setPhase("idle");
        setFile(null);
        setError(null);
        setResult(null);
        setElapsed(0);
        if (timerRef.current) clearInterval(timerRef.current);
    }, []);

    function validateFile(f) {
        if (!f) return "No file selected.";
        if (
            !ACCEPTED_TYPES.includes(f.type) &&
            !f.name.match(/\.mp3$/i)
        ) {
            return "Only MP3 files are supported.";
        }
        if (f.size > MAX_SIZE)
            return `File too large. Maximum ${formatBytes(MAX_SIZE)}.`;
        return null;
    }

    function handleFile(f) {
        const err = validateFile(f);
        if (err) {
            setError(err);
            return;
        }
        setError(null);
        setFile(f);
        setPhase("ready");
    }

    async function reconstruct() {
        if (!file) return;
        setPhase("processing");
        setError(null);
        setElapsed(0);

        const start = Date.now();
        timerRef.current = setInterval(() => {
            setElapsed((Date.now() - start) / 1000);
        }, 100);

        try {
            const form = new FormData();
            form.append("file", file);
            const res = await fetch("/api/model-serve", {
                method: "POST",
                body: form,
            });
            clearInterval(timerRef.current);
            setElapsed((Date.now() - start) / 1000);

            if (!res.ok) {
                const body = await res.json().catch(() => null);
                throw new Error(body?.detail ?? `Server error (${res.status})`);
            }

            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const disposition = res.headers.get("content-disposition") ?? "";
            const nameMatch = disposition.match(/filename="?([^"]+)"?/);
            const outputName =
                nameMatch?.[1] ??
                file.name.replace(/\.\w+$/, "_reconstructed.flac");

            setResult({ url, name: outputName, size: blob.size });
            setPhase("done");
        } catch (err) {
            clearInterval(timerRef.current);
            setError(err.message || "Reconstruction failed.");
            setPhase("ready");
        }
    }

    function download() {
        if (!result) return;
        const a = document.createElement("a");
        a.href = result.url;
        a.download = result.name;
        a.click();
    }

    useEffect(() => {
        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
            if (result?.url) URL.revokeObjectURL(result.url);
        };
    }, [result]);

    return (
        <div className="min-h-screen flex flex-col relative">
            <AmbientBackground />

            <motion.header
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="flex items-center justify-between px-6 py-5 md:px-10 relative z-10"
            >
                <div className="flex items-center gap-2.5">
                    <motion.div
                        className="w-8 h-8 rounded-lg flex items-center justify-center"
                        style={{
                            background: "rgba(139,92,246,0.08)",
                            border: "1px solid rgba(139,92,246,0.12)",
                        }}
                        whileHover={{ scale: 1.06, rotate: -2 }}
                        transition={springSnappy}
                    >
                        <svg
                            width="15"
                            height="15"
                            viewBox="0 0 20 20"
                            fill="none"
                        >
                            <path
                                d="M10 2V18M6 5V15M14 5V15M2 8V12M18 8V12"
                                stroke="var(--color-accent-light)"
                                strokeWidth="2"
                                strokeLinecap="round"
                            />
                        </svg>
                    </motion.div>
                    <span className="text-[15px] font-semibold tracking-tight text-text">
                        Audio
                        <span className="text-accent-light">Recon</span>
                    </span>
                </div>
                <StatusBadge />
            </motion.header>

            <main className="flex-1 flex items-center justify-center px-4 pb-20 relative z-10">
                <div className="w-full max-w-[420px]">
                    <AnimatePresence mode="wait">
                        {phase === "idle" && (
                            <UploadZone
                                key="upload"
                                onFile={handleFile}
                                dragOver={dragOver}
                                setDragOver={setDragOver}
                                inputRef={inputRef}
                            />
                        )}
                        {phase === "ready" && file && (
                            <ReadyCard
                                key="ready"
                                file={file}
                                onReconstruct={reconstruct}
                                onReset={reset}
                            />
                        )}
                        {phase === "processing" && (
                            <ProcessingCard
                                key="processing"
                                file={file}
                                elapsed={elapsed}
                            />
                        )}
                        {phase === "done" && result && (
                            <DoneCard
                                key="done"
                                result={result}
                                elapsed={elapsed}
                                onDownload={download}
                                onReset={reset}
                            />
                        )}
                    </AnimatePresence>

                    <AnimatePresence>
                        {error && (
                            <motion.div
                                initial={{
                                    opacity: 0,
                                    y: 6,
                                    height: 0,
                                    marginTop: 0,
                                }}
                                animate={{
                                    opacity: 1,
                                    y: 0,
                                    height: "auto",
                                    marginTop: 12,
                                }}
                                exit={{
                                    opacity: 0,
                                    y: -4,
                                    height: 0,
                                    marginTop: 0,
                                }}
                                transition={{ duration: 0.2 }}
                                className="rounded-xl px-4 py-3 text-error text-sm overflow-hidden"
                                style={{
                                    background: "rgba(251,113,133,0.06)",
                                    border: "1px solid rgba(251,113,133,0.12)",
                                }}
                            >
                                {error}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </main>

            <motion.footer
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6, duration: 0.5 }}
                className="text-center py-5 relative z-10"
            >
                <span className="text-text-muted/40 text-[10px] font-mono tracking-[0.12em] uppercase">
                    GAN Super-Resolution &middot; 28M params &middot; 44.1kHz
                    stereo
                </span>
            </motion.footer>
        </div>
    );
}
