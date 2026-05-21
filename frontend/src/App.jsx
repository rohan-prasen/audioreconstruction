import { useState, useEffect, useRef, useCallback } from "react";
import LightRays from "./LightRays";

const API_BASE = import.meta.env.VITE_BACKEND_URL || "";
const MAX_SIZE = 25 * 1024 * 1024;
const MAX_RETRIES = 5;
const HEALTH_POLL_MS = 30000;

function getRetryDelay(attempt, retryAfterHeader) {
    if (retryAfterHeader) {
        const secs = parseInt(retryAfterHeader, 10);
        if (!Number.isNaN(secs)) return secs * 1000;
    }
    const base = 3000;
    const delay = Math.min(base * Math.pow(2, attempt), 30000);
    return delay + Math.random() * 1000;
}
const WAVEFORM_BARS = [
    42, 80, 30, 68, 48, 92, 36, 74, 58, 88, 26, 64, 52, 95, 44, 76, 34, 84,
    60,
];

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

export default function App() {
    const [files, setFiles] = useState([]);
    const [notice, setNotice] = useState({
        message: "No files selected.",
        tone: "",
    });
    const [theme, setThemeState] = useState("light");
    const [jobMap, setJobMap] = useState({});
    const [serverStatus, setServerStatus] = useState("unknown");
    const dragDepthRef = useRef(0);
    const addFilesRef = useRef(null);
    const processingRef = useRef(false);
    const jobMapRef = useRef(jobMap);
    const abortControllersRef = useRef({});
    const cancelledRef = useRef(false);
    jobMapRef.current = jobMap;

    const processing = files.some((f) => {
        const s = jobMap[fileKey(f)]?.status;
        return s === "processing" || s === "waiting";
    });
    const doneCount = files.filter(
        (f) => jobMap[fileKey(f)]?.status === "done",
    ).length;
    const allDone = files.length > 0 && doneCount === files.length;
    const dark = theme === "dark";

    const addFiles = useCallback((fileSet) => {
        const incoming = Array.from(fileSet || []);
        if (!incoming.length) return;

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

    function setTheme(t) {
        document.documentElement.dataset.theme = t;
        localStorage.setItem("audio-reconstruction-theme", t);
        setThemeState(t);
    }

    useEffect(() => {
        const saved = localStorage.getItem("audio-reconstruction-theme");
        const preferred = window.matchMedia("(prefers-color-scheme: dark)")
            .matches
            ? "dark"
            : "light";
        setTheme(saved || preferred);
    }, []);

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

    useEffect(() => {
        let active = true;
        let failCount = 0;
        const check = async () => {
            try {
                const res = await fetch(`${API_BASE}/health-check`);
                if (res.ok && active) {
                    const data = await res.json();
                    setServerStatus(data.status === "ok" ? "online" : "degraded");
                    failCount = 0;
                } else {
                    failCount++;
                }
            } catch {
                failCount++;
            }
            if (failCount >= 3 && active) setServerStatus("offline");
        };
        check();
        const interval = setInterval(check, HEALTH_POLL_MS);
        return () => {
            active = false;
            clearInterval(interval);
        };
    }, []);

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

    let statusText = "Waiting for MP3";
    let statusClass = "";
    if (files.length > 0) {
        if (processing) {
            statusText = "Reconstructing…";
            statusClass = " processing";
        } else if (allDone) {
            statusText = "Complete";
            statusClass = " complete";
        } else {
            statusText = "Ready to reconstruct";
            statusClass = " ready";
        }
    }

    const processingIndex = files.findIndex((f) => {
        const s = jobMap[fileKey(f)]?.status;
        return s === "processing" || s === "waiting";
    });

    return (
        <>
            <div className="light-rays-bg">
                <LightRays
                    raysOrigin="top-center"
                    raysColor={dark ? "#a78bfa" : "#6366f1"}
                    raysSpeed={0.4}
                    lightSpread={0.7}
                    rayLength={1.5}
                    followMouse={true}
                    mouseInfluence={0.05}
                    noiseAmount={0.03}
                    distortion={0.02}
                    fadeDistance={1.0}
                    saturation={0.8}
                />
            </div>

            <nav className="nav" aria-label="Primary">
                <a
                    className="logo"
                    href="#"
                    aria-label="AudioReconstruction home"
                >
                    AudioReconstruction
                </a>
                <div className="nav-actions">
                    <button
                        className="theme-toggle"
                        type="button"
                        aria-pressed={String(dark)}
                        onClick={() => setTheme(dark ? "light" : "dark")}
                    >
                        <span aria-hidden="true">{dark ? "L" : "D"}</span>
                        <span className="theme-label">
                            {dark ? "Light" : "Dark"}
                        </span>
                    </button>
                    <a
                        className="star-link"
                        href="https://github.com/rohan-prasen/audioreconstruction"
                        target="_blank"
                        rel="noreferrer"
                        aria-label="Star AudioReconstruction on GitHub"
                    >
                        <svg viewBox="0 0 16 16" aria-hidden="true">
                            <path d="M8 0C3.58 0 0 3.67 0 8.2c0 3.62 2.29 6.69 5.47 7.77.4.08.55-.18.55-.4l-.01-1.4c-2.23.5-2.7-1.1-2.7-1.1-.36-.95-.89-1.2-.89-1.2-.73-.51.06-.5.06-.5.8.06 1.23.85 1.23.85.72 1.26 1.88.9 2.34.69.07-.54.28-.9.51-1.11-1.78-.21-3.64-.91-3.64-4.04 0-.9.31-1.63.82-2.2-.08-.21-.36-1.05.08-2.18 0 0 .67-.22 2.2.84A7.42 7.42 0 0 1 8 3.94c.68 0 1.36.09 2 .27 1.52-1.06 2.19-.84 2.19-.84.44 1.13.16 1.97.08 2.18.51.57.82 1.3.82 2.2 0 3.14-1.87 3.83-3.65 4.03.29.26.54.76.54 1.53l-.01 2.26c0 .22.15.48.55.4A8.13 8.13 0 0 0 16 8.2C16 3.67 12.42 0 8 0Z" />
                        </svg>
                        <span className="star-text">Star</span>
                    </a>
                </div>
            </nav>

            <main className="page">
                <section className="app-grid" aria-labelledby="pageTitle">
                    <div className="hero">
                        <div>
                            <span className="eyebrow">
                                MP3 intake / 25 MB ceiling
                            </span>
                            <h1 id="pageTitle">Repair the signal.</h1>
                            <p className="intro">
                                Drop an MP3 anywhere on this page or use the
                                upload button. AudioReconstruction accepts only
                                MPEG audio files up to 25 MB per file, then
                                queues them for inspection.
                            </p>
                        </div>

                        <div
                            className="spec-strip"
                            aria-label="Upload constraints"
                        >
                            <div className="spec">
                                <b>MP3</b>
                                <span>Accepted format</span>
                            </div>
                            <div className="spec">
                                <b>25MB</b>
                                <span>Max file size</span>
                            </div>
                            <div className="spec">
                                <b>{files.length}</b>
                                <span>Queued tracks</span>
                            </div>
                        </div>
                    </div>

                    <section
                        className="drop-shell"
                        aria-label="Upload MP3 files"
                    >
                        <header className="drop-head">
                            <strong>Reconstruction queue</strong>
                            <span className={`status-pill${statusClass}`}>
                                {statusText}
                            </span>
                        </header>

                        <div className="drop-zone">
                            <div className="drop-core">
                                <div className="waveform" aria-hidden="true">
                                    {WAVEFORM_BARS.map((bar, i) => (
                                        <span
                                            key={i}
                                            style={{ "--bar": `${bar}%` }}
                                        />
                                    ))}
                                </div>

                                <h2 className="drop-title">Drop audio here</h2>
                                <p className="drop-copy">
                                    The entire page is an upload target. Invalid
                                    files are rejected before they enter the
                                    queue.
                                </p>

                                <label className="upload-button">
                                    Choose MP3 files
                                    <input
                                        type="file"
                                        accept=".mp3,audio/mpeg"
                                        multiple
                                        onChange={(e) => {
                                            addFiles(e.target.files);
                                            e.target.value = "";
                                        }}
                                    />
                                </label>

                                <div
                                    className={`notice${notice.tone ? ` ${notice.tone}` : ""}`}
                                    role="status"
                                    aria-live="polite"
                                >
                                    {notice.message}
                                </div>

                                <div
                                    className="file-list"
                                    aria-label="Selected files"
                                >
                                    {files.length === 0 ? (
                                        <div className="empty-row">
                                            Queue empty
                                        </div>
                                    ) : (
                                        files.map((file, index) => {
                                            const key = fileKey(file);
                                            const job = jobMap[key];
                                            const status = job?.status;

                                            return (
                                                <div
                                                    className="file-row"
                                                    key={key}
                                                >
                                                    <div>
                                                        <p
                                                            className="file-name"
                                                            title={file.name}
                                                        >
                                                            {file.name}
                                                        </p>
                                                        <span className="file-meta">
                                                            {status === "done" &&
                                                            job.result
                                                                ? `${formatSize(job.result.size)} FLAC output`
                                                                : `${formatSize(file.size)} / MPEG audio`}
                                                        </span>
                                                        {status === "error" && (
                                                            <span className="file-error">
                                                                {job.error}
                                                            </span>
                                                        )}
                                                    </div>
                                                    {status ===
                                                        "waiting" ? (
                                                        <div className="file-actions">
                                                            <span className="file-processing">
                                                                Retrying&hellip;
                                                            </span>
                                                            <button
                                                                className="cancel-file"
                                                                type="button"
                                                                aria-label={`Cancel ${file.name}`}
                                                                onClick={() =>
                                                                    abortControllersRef.current[key]?.abort()
                                                                }
                                                            >
                                                                &times;
                                                            </button>
                                                        </div>
                                                    ) : status ===
                                                      "processing" ? (
                                                        <div className="file-actions">
                                                            <span className="file-processing">
                                                                Processing&hellip;
                                                            </span>
                                                            <button
                                                                className="cancel-file"
                                                                type="button"
                                                                aria-label={`Cancel ${file.name}`}
                                                                onClick={() =>
                                                                    abortControllersRef.current[key]?.abort()
                                                                }
                                                            >
                                                                &times;
                                                            </button>
                                                        </div>
                                                    ) : status === "done" ? (
                                                        <div className="file-actions">
                                                            <button
                                                                className="download-file"
                                                                type="button"
                                                                onClick={() =>
                                                                    downloadResult(
                                                                        key,
                                                                    )
                                                                }
                                                            >
                                                                Download
                                                            </button>
                                                            <button
                                                                className="remove-file"
                                                                type="button"
                                                                aria-label={`Remove ${file.name}`}
                                                                onClick={() =>
                                                                    removeFile(
                                                                        index,
                                                                    )
                                                                }
                                                            >
                                                                &times;
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <button
                                                            className="remove-file"
                                                            type="button"
                                                            aria-label={`Remove ${file.name}`}
                                                            onClick={() =>
                                                                removeFile(
                                                                    index,
                                                                )
                                                            }
                                                        >
                                                            Remove
                                                        </button>
                                                    )}
                                                </div>
                                            );
                                        })
                                    )}
                                </div>
                            </div>
                        </div>

                        <footer className="drop-foot">
                            {files.length > 0 ? (
                                <>
                                    <span>
                                        {processing
                                            ? `Processing ${processingIndex + 1} of ${files.length}`
                                            : allDone
                                              ? "All files reconstructed"
                                              : `${files.length} file${files.length === 1 ? "" : "s"} queued`}
                                    </span>
                                    {allDone ? (
                                        <button
                                            className="clear-button"
                                            type="button"
                                            onClick={clearQueue}
                                        >
                                            Clear queue
                                        </button>
                                    ) : processing ? (
                                        <button
                                            className="cancel-button"
                                            type="button"
                                            onClick={cancelAll}
                                        >
                                            Cancel
                                        </button>
                                    ) : (
                                        <button
                                            className="reconstruct-button"
                                            type="button"
                                            onClick={reconstructAll}
                                            disabled={
                                                serverStatus === "offline"
                                            }
                                            title={
                                                serverStatus === "offline"
                                                    ? "Server is offline"
                                                    : undefined
                                            }
                                        >
                                            {serverStatus === "offline"
                                                ? "Server Offline"
                                                : "Reconstruct"}
                                        </button>
                                    )}
                                </>
                            ) : (
                                <>
                                    <span>Drag state: page-wide capture</span>
                                    <span
                                        className={`server-status ${serverStatus}`}
                                    >
                                        {serverStatus === "online"
                                            ? "Server online"
                                            : serverStatus === "offline"
                                              ? "Server offline"
                                              : serverStatus === "degraded"
                                                ? "Server degraded"
                                                : "Checking server..."}
                                    </span>
                                </>
                            )}
                        </footer>
                    </section>
                </section>
            </main>
        </>
    );
}
