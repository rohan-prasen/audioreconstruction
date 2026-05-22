import { useState, useEffect, useRef, useCallback, useMemo } from "react";

const API_BASE = import.meta.env.VITE_BACKEND_URL || "";
const MAX_SIZE = 25 * 1024 * 1024;
const MAX_RETRIES = 5;

function getRetryDelay(attempt, retryAfterHeader) {
    if (retryAfterHeader) {
        const secs = parseInt(retryAfterHeader, 10);
        if (!Number.isNaN(secs)) return secs * 1000;
    }
    const base = 3000;
    const delay = Math.min(base * Math.pow(2, attempt), 30000);
    return delay + Math.random() * 1000;
}

function formatSize(bytes) {
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function isMp3(file) {
    const nameOk = file.name.toLowerCase().endsWith(".mp3");
    const typeOk =
        file.type === "audio/mpeg" ||
        file.type === "audio/mp3" ||
        file.type === "";
    return nameOk && typeOk;
}

function validateFile(file) {
    if (!isMp3(file))
        return `${file.name} rejected: only .mp3 files are supported.`;
    if (file.size > MAX_SIZE)
        return `${file.name} rejected: ${formatSize(file.size)} exceeds 25 MB.`;
    return "";
}

function fileKey(file) {
    return `${file.name}-${file.size}-${file.lastModified}`;
}

function SunIcon(props) {
    return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
            strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
            <circle cx="12" cy="12" r="4"></circle>
            <path d="M12 2.5v2.2M12 19.3v2.2M4.57 4.57l1.56 1.56M17.87 17.87l1.56 1.56M2.5 12h2.2M19.3 12h2.2M4.57 19.43l1.56-1.56M17.87 6.13l1.56-1.56"></path>
        </svg>
    );
}

function MoonIcon(props) {
    return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
            strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
            <path d="M20.5 14.4A7.9 7.9 0 0 1 9.6 3.5a8.7 8.7 0 1 0 10.9 10.9Z"></path>
        </svg>
    );
}

function DesktopIcon(props) {
    return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
            strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
            <rect x="3.5" y="4.5" width="17" height="11.5" rx="2.2"></rect>
            <path d="M9 20h6M12 16v4"></path>
        </svg>
    );
}

function FileCard({ file, job, index, onRemove, onCancel, onDownload }) {
    const status = job?.status; // "processing" | "waiting" | "done" | "error" | undefined

    const cardClass = [
        "file-card",
        status === "done" ? "done" : "",
        status === "error" ? "failed" : "",
    ].filter(Boolean).join(" ");

    const progress = status === "done" ? 100 : (status === "processing" || status === "waiting") ? 42 : 0;
    const isWorking = status === "processing" || status === "waiting";

    const statusLabel = status === "processing" ? "Processing…"
        : status === "waiting" ? "Retrying…"
        : status === "done" ? "Done"
        : status === "error" ? "Failed"
        : "Ready";

    return (
        <article
            className={cardClass + (isWorking ? " " + (status === "waiting" ? "uploading" : "processing") : "")}
            style={{ "--progress": `${progress}%` }}
        >
            <div className="file-top">
                <div className="filename" title={file.name}>{file.name}</div>
                <div className="file-actions">
                    <span className="status" aria-live="polite">{statusLabel}</span>
                    {isWorking && (
                        <button className="mini-action secondary" type="button" onClick={onCancel}>
                            Cancel
                        </button>
                    )}
                    {status === "done" && (
                        <button className="mini-action" type="button" onClick={onDownload}>
                            Download
                        </button>
                    )}
                    {!isWorking && (
                        <button
                            className="remove-btn"
                            type="button"
                            aria-label={`Remove ${file.name}`}
                            onClick={() => onRemove(index)}
                        >
                            &times;
                        </button>
                    )}
                </div>
            </div>
            {status === "error" && (
                <div className="error-line">{job.error || "Reconstruction failed."}</div>
            )}
            <div className="progress-track" aria-hidden={!isWorking && status !== "done"}>
                <div className="progress-fill"></div>
            </div>
        </article>
    );
}

function WakeUpToast({ visible }) {
    return (
        <div className={`wakeup-toast${visible ? "" : " hidden"}`} role="status" aria-live="polite">
            <span className="wakeup-spinner" aria-hidden="true" />
            <span className="wakeup-text">
                <span className="wakeup-title">Waking up the model…</span>
                <span className="wakeup-sub">First request takes ~30–60 s</span>
            </span>
        </div>
    );
}

export default function App() {
    const [files, setFiles] = useState([]);
    const [notice, setNotice] = useState({
        message: "No files selected.",
        tone: "",
    });
    const [jobMap, setJobMap] = useState({});
    const [themeChoice, setThemeChoice] = useState(
        () => localStorage.getItem("audio-reconstruction-theme") || "system"
    );
    const [themeMenuOpen, setThemeMenuOpen] = useState(false);
    const [systemDark, setSystemDark] = useState(
        () => window.matchMedia("(prefers-color-scheme: dark)").matches
    );
    const [scrolled, setScrolled] = useState(false);
    const [dragState, setDragState] = useState("idle");

    const dragDepthRef = useRef(0);
    const addFilesRef = useRef(null);
    const processingRef = useRef(false);
    const jobMapRef = useRef(jobMap);
    const abortControllersRef = useRef({});
    const cancelledRef = useRef(false);
    const themeMenuRef = useRef(null);

    jobMapRef.current = jobMap;

    const activeTheme = themeChoice === "system" ? (systemDark ? "dark" : "light") : themeChoice;
    // eslint-disable-next-line no-unused-vars
    const dark = activeTheme === "dark"; // kept for any future logic that references it

    const coldStarting = Object.values(jobMap).some((j) => j.status === "waiting");

    const processing = files.some((f) => {
        const s = jobMap[fileKey(f)]?.status;
        return s === "processing" || s === "waiting";
    });
    const doneCount = files.filter(
        (f) => jobMap[fileKey(f)]?.status === "done",
    ).length;
    const allDone = files.length > 0 && doneCount === files.length;

    const dropClass = useMemo(() => {
        const parts = ["dropzone"];
        if (dragState === "accept") parts.push("drag-accept");
        if (dragState === "reject") parts.push("drag-reject");
        return parts.join(" ");
    }, [dragState]);

    const addFiles = useCallback((fileSet) => {
        const incoming = Array.from(fileSet || []);
        if (!incoming.length) return;

        fetch(`${API_BASE}/health-check`).catch(() => {});

        setFiles((prev) => {
            const errors = [];
            const next = [...prev];

            for (const file of incoming) {
                const error = validateFile(file);
                if (error) {
                    errors.push(error);
                    continue;
                }
                const duplicate = next.some(
                    (item) =>
                        item.name === file.name &&
                        item.size === file.size &&
                        item.lastModified === file.lastModified,
                );
                if (!duplicate) {
                    next.push(file);
                }
            }

            if (errors.length) {
                setNotice({ message: errors[0], tone: "error" });
            } else {
                setNotice({
                    message: `${incoming.length} file${incoming.length === 1 ? "" : "s"} checked. ${next.length} ready.`,
                    tone: "success",
                });
            }

            return next;
        });
    }, []);

    addFilesRef.current = addFiles;

    function removeFile(index) {
        setFiles((prev) => {
            const removed = prev[index];
            const key = fileKey(removed);

            abortControllersRef.current[key]?.abort();
            delete abortControllersRef.current[key];

            setJobMap((prevMap) => {
                const next = { ...prevMap };
                if (next[key]?.result?.url)
                    URL.revokeObjectURL(next[key].result.url);
                delete next[key];
                return next;
            });

            const next = [...prev.slice(0, index), ...prev.slice(index + 1)];
            setNotice({
                message: next.length
                    ? `${next.length} file${next.length === 1 ? "" : "s"} ready.`
                    : "Queue empty.",
                tone: next.length ? "success" : "",
            });
            return next;
        });
    }

    function clearQueue() {
        Object.values(jobMapRef.current).forEach((job) => {
            if (job.result?.url) URL.revokeObjectURL(job.result.url);
        });
        setFiles([]);
        setJobMap({});
        setNotice({ message: "No files selected.", tone: "" });
    }

    // eslint-disable-next-line no-unused-vars
    function cancelAll() {
        cancelledRef.current = true;
        Object.values(abortControllersRef.current).forEach((c) => c.abort());
        abortControllersRef.current = {};
        setJobMap((prev) => {
            const next = { ...prev };
            for (const k of Object.keys(next)) {
                if (next[k].status === "processing" || next[k].status === "waiting") {
                    delete next[k];
                }
            }
            return next;
        });
        processingRef.current = false;
        setNotice({ message: "Reconstruction cancelled.", tone: "" });
    }

    async function reconstructAll() {
        if (processingRef.current) return;
        processingRef.current = true;
        cancelledRef.current = false;

        const filesToProcess = files.filter((f) => {
            const status = jobMap[fileKey(f)]?.status;
            return !status || status === "idle" || status === "error";
        });

        for (const file of filesToProcess) {
            if (cancelledRef.current) break;
            const key = fileKey(file);
            const controller = new AbortController();
            abortControllersRef.current[key] = controller;

            setJobMap((prev) => ({
                ...prev,
                [key]: { status: "processing" },
            }));

            let succeeded = false;
            for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
                if (controller.signal.aborted) break;
                try {
                    const form = new FormData();
                    form.append("file", file);
                    const res = await fetch(`${API_BASE}/model-serve`, {
                        method: "POST",
                        body: form,
                        signal: controller.signal,
                    });

                    const retryable =
                        res.status === 429 || res.status === 503 || res.status === 504;
                    if (retryable && attempt < MAX_RETRIES) {
                        const retryAfter =
                            res.headers.get("retry-after");
                        const delay = getRetryDelay(
                            attempt,
                            retryAfter,
                        );
                        setJobMap((prev) => ({
                            ...prev,
                            [key]: { status: "waiting" },
                        }));
                        await new Promise((r) => setTimeout(r, delay));
                        continue;
                    }

                    if (!res.ok) {
                        const body = await res.json().catch(() => null);
                        throw new Error(
                            body?.detail ??
                                `Server error (${res.status})`,
                        );
                    }

                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    const disposition =
                        res.headers.get("content-disposition") ?? "";
                    const nameMatch =
                        disposition.match(/filename="?([^"]+)"?/);
                    const outputName =
                        nameMatch?.[1] ??
                        file.name.replace(
                            /\.\w+$/,
                            "_reconstructed.flac",
                        );

                    setJobMap((prev) => ({
                        ...prev,
                        [key]: {
                            status: "done",
                            result: {
                                url,
                                name: outputName,
                                size: blob.size,
                            },
                        },
                    }));
                    succeeded = true;
                    break;
                } catch (err) {
                    if (err.name === "AbortError") {
                        setJobMap((prev) => {
                            const next = { ...prev };
                            delete next[key];
                            return next;
                        });
                        break;
                    }
                    if (attempt < MAX_RETRIES) continue;
                    setJobMap((prev) => ({
                        ...prev,
                        [key]: {
                            status: "error",
                            error:
                                err.message ||
                                "Reconstruction failed",
                        },
                    }));
                }
            }

            delete abortControllersRef.current[key];

            if (
                !succeeded &&
                !controller.signal.aborted &&
                jobMapRef.current[key]?.status === "waiting"
            ) {
                setJobMap((prev) => ({
                    ...prev,
                    [key]: {
                        status: "error",
                        error: "Server busy — retries exhausted. Try again later.",
                    },
                }));
            }
        }

        processingRef.current = false;
    }

    function downloadResult(key) {
        const job = jobMap[key];
        if (!job?.result) return;
        const a = document.createElement("a");
        a.href = job.result.url;
        a.download = job.result.name;
        a.click();
    }

    // Apply theme
    useEffect(() => {
        document.documentElement.dataset.theme = activeTheme;
        localStorage.setItem("audio-reconstruction-theme", themeChoice);
    }, [activeTheme, themeChoice]);

    // System media query listener
    useEffect(() => {
        const media = window.matchMedia("(prefers-color-scheme: dark)");
        const onMedia = (e) => setSystemDark(e.matches);
        media.addEventListener("change", onMedia);
        return () => media.removeEventListener("change", onMedia);
    }, []);

    // Scroll listener for navbar
    useEffect(() => {
        const onScroll = () => setScrolled(window.scrollY > 8);
        onScroll();
        window.addEventListener("scroll", onScroll, { passive: true });
        return () => window.removeEventListener("scroll", onScroll);
    }, []);

    // Theme menu close on outside click or Escape
    useEffect(() => {
        if (!themeMenuOpen) return;
        const onPointer = (e) => {
            if (themeMenuRef.current && !themeMenuRef.current.contains(e.target))
                setThemeMenuOpen(false);
        };
        const onKey = (e) => { if (e.key === "Escape") setThemeMenuOpen(false); };
        window.addEventListener("pointerdown", onPointer);
        window.addEventListener("keydown", onKey);
        return () => {
            window.removeEventListener("pointerdown", onPointer);
            window.removeEventListener("keydown", onKey);
        };
    }, [themeMenuOpen]);

    // Window-level drag-drop handlers (adds/removes body.dragging class)
    useEffect(() => {
        function prevent(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        function onDragEnter(e) {
            prevent(e);
            dragDepthRef.current += 1;
            document.body.classList.add("dragging");
        }

        function onDragOver(e) {
            prevent(e);
        }

        function onDragLeave(e) {
            prevent(e);
            dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
            if (dragDepthRef.current === 0) {
                document.body.classList.remove("dragging");
            }
        }

        function onDrop(e) {
            prevent(e);
            dragDepthRef.current = 0;
            document.body.classList.remove("dragging");
            addFilesRef.current(e.dataTransfer.files);
        }

        window.addEventListener("dragenter", onDragEnter);
        window.addEventListener("dragover", onDragOver);
        window.addEventListener("dragleave", onDragLeave);
        window.addEventListener("drop", onDrop);

        return () => {
            window.removeEventListener("dragenter", onDragEnter);
            window.removeEventListener("dragover", onDragOver);
            window.removeEventListener("dragleave", onDragLeave);
            window.removeEventListener("drop", onDrop);
        };
    }, []);


    // Cleanup on unmount: abort requests + revoke object URLs
    useEffect(() => {
        return () => {
            Object.values(abortControllersRef.current).forEach((c) =>
                c.abort(),
            );
            Object.values(jobMapRef.current).forEach((job) => {
                if (job.result?.url) URL.revokeObjectURL(job.result.url);
            });
        };
    }, []);

    return (
        <>
        <WakeUpToast visible={coldStarting} />
        <main
            className="app"
            onDragOver={(e) => {
                e.preventDefault();
                const items = Array.from(e.dataTransfer.items || []);
                const hasReject = items.some(item => item.kind === "file" && item.type && item.type !== "audio/mpeg");
                setDragState(hasReject ? "reject" : "accept");
            }}
            onDragLeave={() => setDragState("idle")}
            onDrop={(e) => { e.preventDefault(); setDragState("idle"); }}
        >
            <nav className={`navbar${scrolled ? " scrolled" : ""}`} aria-label="Primary">
                <a className="wordmark" href="#" aria-label="Open AudioReconstruction home">
                    <span className="wordmark-dot" aria-hidden="true"></span>
                    <span className="wordmark-text">AudioReconstruction</span>
                </a>
                <div className="nav-spacer"></div>
                <div className="theme-menu-wrap" ref={themeMenuRef}>
                    <button
                        className="theme-trigger"
                        type="button"
                        aria-label="Theme menu"
                        aria-haspopup="menu"
                        aria-expanded={themeMenuOpen}
                        onClick={() => setThemeMenuOpen(open => !open)}
                    >
                        {themeChoice === "light" && <SunIcon />}
                        {themeChoice === "dark" && <MoonIcon />}
                        {themeChoice === "system" && <DesktopIcon />}
                    </button>
                    <div className={`theme-menu${themeMenuOpen ? " open" : ""}`} role="menu" aria-label="Choose theme">
                        {[["light", "Light", <SunIcon />], ["dark", "Dark", <MoonIcon />], ["system", "System", <DesktopIcon />]].map(([value, label, icon]) => (
                            <button key={value} className="theme-option" type="button" role="menuitemradio"
                                aria-checked={themeChoice === value}
                                onClick={() => { setThemeChoice(value); setThemeMenuOpen(false); }}>
                                {icon}<span>{label}</span>
                            </button>
                        ))}
                    </div>
                </div>
                <a
                    className="github-link"
                    href="https://github.com/rohan-prasen/audioreconstruction"
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label="Star AudioReconstruction on GitHub"
                >
                    <span>Star</span>
                    <svg width="19" height="19" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                        <path d="M12 .5A11.5 11.5 0 0 0 8.36 22.9c.58.11.79-.25.79-.56v-2.02c-3.22.7-3.9-1.38-3.9-1.38-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08-.7.08-.7 1.16.08 1.78 1.2 1.78 1.2 1.04 1.77 2.72 1.26 3.38.96.1-.75.4-1.26.73-1.55-2.57-.29-5.28-1.29-5.28-5.73 0-1.27.45-2.3 1.2-3.12-.12-.29-.52-1.47.11-3.08 0 0 .98-.31 3.2 1.2a11.1 11.1 0 0 1 5.83 0c2.22-1.51 3.2-1.2 3.2-1.2.63 1.61.23 2.79.11 3.08.75.82 1.2 1.85 1.2 3.12 0 4.46-2.71 5.43-5.3 5.72.42.37.79 1.09.79 2.2v3.26c0 .31.21.68.8.56A11.5 11.5 0 0 0 12 .5Z" />
                    </svg>
                </a>
            </nav>

            <section className="hero" aria-labelledby="headline">
                <div className="mesh-stage" aria-hidden="true">
                    <div className="blob blob-a"></div>
                    <div className="blob blob-b"></div>
                    <div className="blob blob-c"></div>
                    <div className="blob blob-d"></div>
                </div>

                <div className="hero-inner">
                    <div className="headline-wrap">
                        <h1 id="headline">Restore your lossy music to lossless.</h1>
                        <p className="subhead">
                            Give me old and rusty audio. I will make them as good as{" "}
                            <span className="subhead-emphasis">new</span>!
                        </p>
                    </div>

                    <div className="dropzone-shell">
                        <label
                            className={dropClass}
                            onMouseEnter={() => setDragState(s => s === "idle" ? "hover" : s)}
                            onMouseLeave={() => setDragState("idle")}
                        >
                            <input
                                type="file"
                                accept="audio/mpeg,.mp3"
                                multiple
                                onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }}
                                style={{ display: "none" }}
                            />
                            <span className="upload-head">
                                <span>
                                    <span className="upload-title">Audio upload</span>
                                    <span className="upload-caption">Review your queue before reconstruction starts.</span>
                                </span>
                                <span className="upload-badge">FLAC output</span>
                            </span>
                            <span className="upload-well">
                                <span className="upload-icon" aria-hidden="true">
                                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                        strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                                        <path d="M12 17V5" /><path d="m7 10 5-5 5 5" /><path d="M5 19h14" />
                                    </svg>
                                </span>
                                <span className="upload-copy">
                                    <span className="drop-primary">
                                        {dragState === "reject" ? "MP3 only" : "Drag and drop or choose MP3 files"}
                                    </span>
                                    <span className="drop-secondary">Click anywhere in this panel to browse.</span>
                                    <span className="drop-tertiary">Files stay in queue until you press Start reconstruction.</span>
                                </span>
                            </span>
                            <span className="upload-meta" aria-label="Upload constraints">
                                <span><strong>MP3 only</strong>{" · "}25 MB per file</span>
                                <span className="upload-format">28M GAN</span>
                            </span>
                        </label>
                        <div className="inline-message" role="status" aria-live="polite">
                            {notice.tone === "error" ? notice.message : ""}
                        </div>
                    </div>

                    {files.length > 0 && (
                        <section className="queue" aria-label="Reconstruction queue">
                            {files.map((file, index) => {
                                const key = fileKey(file);
                                const job = jobMap[key];
                                return (
                                    <FileCard
                                        key={key}
                                        file={file}
                                        job={job}
                                        index={index}
                                        onRemove={removeFile}
                                        onCancel={() => abortControllersRef.current[key]?.abort()}
                                        onDownload={() => downloadResult(key)}
                                    />
                                );
                            })}
                        </section>
                    )}

                    {files.length > 0 && (
                        <div className="start-wrap">
                            {allDone ? (
                                <button className="start-button" type="button" onClick={clearQueue}>
                                    Clear queue
                                </button>
                            ) : processing ? (
                                <button className="start-button" type="button" disabled>
                                    <span className="spinner" aria-hidden="true"></span>
                                    Reconstructing…
                                </button>
                            ) : (
                                <button
                                    className="start-button"
                                    type="button"
                                    onClick={reconstructAll}
                                >
                                    Start reconstruction
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </section>
        </main>
        </>
    );
}
