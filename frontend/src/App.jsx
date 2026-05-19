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

const spring = { type: "spring", stiffness: 300, damping: 30 };
const springGentle = { type: "spring", stiffness: 200, damping: 25 };

const cardVariants = {
    hidden: { opacity: 0, y: 24, scale: 0.97 },
    visible: {
        opacity: 1,
        y: 0,
        scale: 1,
        transition: { ...springGentle, staggerChildren: 0.06 },
    },
    exit: { opacity: 0, y: -16, scale: 0.98, transition: { duration: 0.2 } },
};

const itemVariants = {
    hidden: { opacity: 0, y: 12 },
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
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3, ...springGentle }}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-raised/60 border border-border-subtle ${textColor} text-xs font-mono`}
        >
            <motion.span
                className={`w-1.5 h-1.5 rounded-full ${dotColor}`}
                animate={
                    status.checking ? { opacity: [0.4, 1, 0.4] } : undefined
                }
                transition={
                    status.checking
                        ? { duration: 1.5, repeat: Infinity }
                        : undefined
                }
            />
            {label}
        </motion.div>
    );
}

function WaveformVisualizer({ active, barCount = 40 }) {
    return (
        <div className="flex items-end justify-center gap-[2px] h-20 px-2">
            {Array.from({ length: barCount }, (_, i) => {
                const center = Math.abs(i - barCount / 2) / (barCount / 2);
                const baseHeight = active
                    ? 15 + (1 - center) * 85
                    : 8 + (1 - center) * 24;
                const delay = i * 0.04;
                return (
                    <motion.div
                        key={i}
                        className="w-[2.5px] rounded-full origin-bottom"
                        initial={{ scaleY: 0 }}
                        animate={{ scaleY: 1 }}
                        transition={{ delay: delay * 0.5, ...spring }}
                        style={{
                            height: `${baseHeight}%`,
                            background: active
                                ? `linear-gradient(to top, var(--color-accent), var(--color-cyan))`
                                : `linear-gradient(to top, var(--color-accent-light), var(--color-cyan))`,
                            animation: active
                                ? `wave-bar 0.7s ease-in-out ${delay}s infinite`
                                : "none",
                            opacity: active ? 0.9 : 0.2,
                            transition:
                                "opacity 0.6s ease, background 0.6s ease",
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
            <motion.div
                className="absolute w-[600px] h-[600px] rounded-full"
                style={{
                    background:
                        "radial-gradient(circle, rgba(124,58,237,0.07) 0%, transparent 70%)",
                    top: "-10%",
                    left: "30%",
                }}
                animate={{
                    x: [0, 40, -20, 0],
                    y: [0, -30, 20, 0],
                }}
                transition={{
                    duration: 20,
                    repeat: Infinity,
                    ease: "easeInOut",
                }}
            />
            <motion.div
                className="absolute w-[500px] h-[500px] rounded-full"
                style={{
                    background:
                        "radial-gradient(circle, rgba(56,189,248,0.04) 0%, transparent 70%)",
                    bottom: "-5%",
                    right: "10%",
                }}
                animate={{
                    x: [0, -30, 20, 0],
                    y: [0, 20, -30, 0],
                }}
                transition={{
                    duration: 25,
                    repeat: Infinity,
                    ease: "easeInOut",
                }}
            />
            <div
                className="absolute inset-0 opacity-[0.015]"
                style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
                    backgroundRepeat: "repeat",
                }}
            />
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
                className="relative rounded-2xl border border-dashed overflow-hidden"
                animate={{
                    borderColor: dragOver
                        ? "rgba(124,58,237,0.6)"
                        : "rgba(124,58,237,0.2)",
                    backgroundColor: dragOver
                        ? "rgba(124,58,237,0.06)"
                        : "rgba(19,16,30,0.8)",
                }}
                whileHover={{
                    borderColor: "rgba(124,58,237,0.4)",
                    backgroundColor: "rgba(19,16,30,0.9)",
                }}
                transition={{ duration: 0.25 }}
                style={{
                    boxShadow: dragOver
                        ? "0 0 80px rgba(124,58,237,0.12), inset 0 1px 0 rgba(255,255,255,0.03)"
                        : "0 0 40px rgba(124,58,237,0.04), inset 0 1px 0 rgba(255,255,255,0.02)",
                }}
            >
                <div className="px-10 py-14 flex flex-col items-center text-center">
                    <input
                        ref={inputRef}
                        type="file"
                        accept=".mp3,.flac,.wav"
                        className="hidden"
                        onChange={(e) => {
                            const f = e.target.files?.[0];
                            if (f) onFile(f);
                            e.target.value = "";
                        }}
                    />

                    <motion.div variants={itemVariants} className="mb-6">
                        <motion.div
                            className="w-16 h-16 rounded-2xl bg-accent/8 border border-accent/15 flex items-center justify-center"
                            whileHover={{ scale: 1.05, rotate: 2 }}
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
                                <path d="M12 17V3M12 3L7 8M12 3L17 8" />
                                <path d="M4 15v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
                            </svg>
                        </motion.div>
                    </motion.div>

                    <motion.p
                        variants={itemVariants}
                        className="text-text text-base font-medium mb-1.5 tracking-tight"
                    >
                        Drop audio file to reconstruct
                    </motion.p>
                    <motion.p
                        variants={itemVariants}
                        className="text-text-muted text-sm mb-5"
                    >
                        or click to browse your files
                    </motion.p>

                    <motion.div
                        variants={itemVariants}
                        className="flex items-center gap-3 text-xs text-text-muted"
                    >
                        <span className="px-2.5 py-1 rounded-md bg-surface-bright/60 text-text-secondary font-mono">
                            MP3
                        </span>
                        <span className="text-text-muted/60 mx-1">|</span>
                        <span className="text-text-muted font-mono">
                            {formatBytes(MAX_SIZE)} max
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
            className="rounded-2xl border border-border bg-surface/80 backdrop-blur-xl overflow-hidden"
            style={{
                boxShadow:
                    "0 0 40px rgba(124,58,237,0.06), inset 0 1px 0 rgba(255,255,255,0.03)",
            }}
        >
            <div className="p-6 space-y-5">
                <motion.div
                    variants={itemVariants}
                    className="flex items-center gap-3"
                >
                    <div className="w-10 h-10 rounded-xl bg-accent/8 border border-accent/15 flex items-center justify-center shrink-0">
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
                        <p className="text-text text-sm font-medium truncate">
                            {file.name}
                        </p>
                        <p className="text-text-muted text-xs mt-0.5 font-mono">
                            {formatBytes(file.size)}
                        </p>
                    </div>
                    <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={onReset}
                        className="text-text-muted hover:text-error transition-colors p-1.5 rounded-lg hover:bg-error/8 cursor-pointer"
                        aria-label="Remove file"
                    >
                        <svg
                            width="16"
                            height="16"
                            viewBox="0 0 16 16"
                            fill="none"
                        >
                            <path
                                d="M4 4L12 12M12 4L4 12"
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
                        whileHover={{ scale: 1.01, y: -1 }}
                        whileTap={{ scale: 0.98 }}
                        transition={spring}
                        onClick={onReconstruct}
                        className="w-full flex items-center justify-center gap-2.5 px-6 py-3.5 bg-accent text-white font-medium text-sm rounded-xl cursor-pointer border-0"
                        style={{
                            boxShadow:
                                "0 0 20px rgba(124,58,237,0.25), 0 4px 12px rgba(0,0,0,0.3)",
                        }}
                    >
                        <svg
                            width="16"
                            height="16"
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
                        Reconstruct Audio
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
            className="rounded-2xl border border-accent/20 bg-surface/80 backdrop-blur-xl overflow-hidden"
            style={{
                boxShadow:
                    "0 0 80px rgba(124,58,237,0.1), inset 0 1px 0 rgba(255,255,255,0.03)",
            }}
        >
            <div className="p-8 space-y-6">
                <motion.div variants={itemVariants}>
                    <WaveformVisualizer active={true} />
                </motion.div>

                <motion.div
                    variants={itemVariants}
                    className="text-center space-y-1.5"
                >
                    <p className="text-text font-medium text-sm">
                        Reconstructing audio
                    </p>
                    <p className="text-accent-light text-2xl font-mono font-semibold tracking-tight">
                        {formatDuration(elapsed)}
                    </p>
                </motion.div>

                <motion.div variants={itemVariants}>
                    <div className="h-1 rounded-full bg-surface-bright overflow-hidden">
                        <motion.div
                            className="h-full rounded-full"
                            style={{
                                background:
                                    "linear-gradient(90deg, var(--color-accent), var(--color-cyan), var(--color-accent))",
                                backgroundSize: "200% 100%",
                                animation: "shimmer 1.5s linear infinite",
                            }}
                            initial={{ width: "0%" }}
                            animate={{ width: "100%" }}
                            transition={{ duration: 0.6, ease: "easeOut" }}
                        />
                    </div>
                </motion.div>

                <motion.p
                    variants={itemVariants}
                    className="text-text-muted text-xs text-center font-mono truncate"
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
            className="rounded-2xl border border-border bg-surface/80 backdrop-blur-xl overflow-hidden"
            style={{
                boxShadow:
                    "0 0 40px rgba(124,58,237,0.06), inset 0 1px 0 rgba(255,255,255,0.03)",
            }}
        >
            <div className="p-6 space-y-5">
                <motion.div
                    variants={itemVariants}
                    className="flex items-center gap-3"
                >
                    <motion.div
                        className="w-10 h-10 rounded-full bg-success/10 border border-success/20 flex items-center justify-center shrink-0"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{
                            type: "spring",
                            stiffness: 400,
                            damping: 15,
                            delay: 0.2,
                        }}
                    >
                        <motion.svg
                            width="18"
                            height="18"
                            viewBox="0 0 18 18"
                            fill="none"
                            initial={{ pathLength: 0 }}
                            animate={{ pathLength: 1 }}
                            transition={{ delay: 0.4, duration: 0.4 }}
                        >
                            <motion.path
                                d="M4 9L7.5 12.5L14 5.5"
                                stroke="var(--color-success)"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                initial={{ pathLength: 0 }}
                                animate={{ pathLength: 1 }}
                                transition={{ delay: 0.4, duration: 0.4 }}
                            />
                        </motion.svg>
                    </motion.div>
                    <div>
                        <p className="text-success text-sm font-medium">
                            Reconstruction complete
                        </p>
                        <p className="text-text-muted text-xs mt-0.5 font-mono">
                            {formatDuration(elapsed)} elapsed
                        </p>
                    </div>
                </motion.div>

                <motion.div
                    variants={itemVariants}
                    className="rounded-xl bg-surface-raised/60 border border-border-subtle p-4 space-y-2.5"
                >
                    {[
                        ["File", result.name],
                        ["Size", formatBytes(result.size)],
                        ["Format", "FLAC (lossless)"],
                    ].map(([label, value]) => (
                        <div
                            key={label}
                            className="flex items-center justify-between"
                        >
                            <span className="text-text-muted text-xs">
                                {label}
                            </span>
                            <span className="text-text-secondary font-mono text-xs truncate ml-4 max-w-[240px]">
                                {value}
                            </span>
                        </div>
                    ))}
                </motion.div>

                <motion.div variants={itemVariants} className="flex gap-2.5">
                    <motion.button
                        whileHover={{ scale: 1.01, y: -1 }}
                        whileTap={{ scale: 0.98 }}
                        transition={spring}
                        onClick={onDownload}
                        className="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-accent text-white font-medium text-sm rounded-xl cursor-pointer border-0"
                        style={{
                            boxShadow:
                                "0 0 20px rgba(124,58,237,0.25), 0 4px 12px rgba(0,0,0,0.3)",
                        }}
                    >
                        <svg
                            width="16"
                            height="16"
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
                        whileHover={{
                            scale: 1.05,
                            borderColor: "rgba(124,58,237,0.4)",
                        }}
                        whileTap={{ scale: 0.95 }}
                        transition={spring}
                        onClick={onReset}
                        className="px-3.5 py-3 rounded-xl border border-border bg-transparent text-text-secondary cursor-pointer flex items-center justify-center hover:bg-accent/5"
                    >
                        <svg
                            width="16"
                            height="16"
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
            !f.name.match(/\.(mp3|flac|wav)$/i)
        ) {
            return "Unsupported format. Please upload MP3, FLAC, or WAV.";
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
                initial={{ opacity: 0, y: -12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="flex items-center justify-between px-6 py-5 md:px-10 relative z-10"
            >
                <div className="flex items-center gap-3">
                    <motion.div
                        className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/15 flex items-center justify-center"
                        whileHover={{ scale: 1.05, rotate: -3 }}
                        transition={spring}
                    >
                        <svg
                            width="16"
                            height="16"
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
                    <h1 className="text-[15px] font-semibold tracking-tight text-text">
                        Audio
                        <span className="text-accent-light">Recon</span>
                    </h1>
                </div>
                <StatusBadge />
            </motion.header>

            <main className="flex-1 flex items-center justify-center px-4 pb-20 relative z-10">
                <div className="w-full max-w-md">
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
                                initial={{ opacity: 0, y: 8, height: 0 }}
                                animate={{
                                    opacity: 1,
                                    y: 0,
                                    height: "auto",
                                }}
                                exit={{ opacity: 0, y: -4, height: 0 }}
                                transition={{ duration: 0.25 }}
                                className="mt-3 rounded-xl bg-error/8 border border-error/15 px-4 py-3 text-error text-sm overflow-hidden"
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
                className="text-center py-5 text-text-muted/60 text-[11px] font-mono tracking-wider relative z-10"
            >
                GAN Super-Resolution &middot; 28M params &middot; 44.1kHz Stereo
            </motion.footer>
        </div>
    );
}
