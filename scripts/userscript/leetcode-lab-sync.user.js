// ==UserScript==
// @name         LeetCode Lab Sync
// @namespace    https://github.com/rajwav/leetcode
// @version      1.2.0
// @description  Zero-friction, credential-free synchronization of accepted LeetCode solutions to your local LeetCode Lab engine.
// @author       rajwav
// @match        https://leetcode.com/problems/*
// @match        https://leetcode.cn/problems/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function () {
    "use strict";

    // Configuration
    const CONFIG = {
        LOCAL_SERVER_URL: "http://127.0.0.1:8765",
        INGEST_ENDPOINT: "/ingest",
        DEBUG: false,          // Set to true temporarily when debugging
        TOAST_DURATION_MS: 4500,
    };

    function log(...args) {
        if (CONFIG.DEBUG) {
            console.log("[LeetCode Lab]", ...args);
        }
    }

    function warn(...args) {
        console.warn("[LeetCode Lab]", ...args);
    }

    function error(...args) {
        console.error("[LeetCode Lab]", ...args);
    }

    // =========================================================================
    // UI Toast Notification
    // =========================================================================
    function showToast(message, type = "success") {
        // HTML-encode message to prevent XSS via server-returned error strings
        const safe = String(message)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");

        let container = document.getElementById("leetcode-lab-toast-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "leetcode-lab-toast-container";
            container.style.position = "fixed";
            container.style.bottom = "24px";
            container.style.right = "24px";
            container.style.zIndex = "9999999";
            container.style.display = "flex";
            container.style.flexDirection = "column";
            container.style.gap = "10px";
            container.style.fontFamily = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, monospace";
            container.style.fontSize = "13px";
            container.style.pointerEvents = "none";
            (document.body || document.documentElement).appendChild(container);
        }

        const toast = document.createElement("div");
        toast.style.padding = "10px 16px";
        toast.style.borderRadius = "8px";
        toast.style.boxShadow = "0 6px 16px rgba(0, 0, 0, 0.4)";
        toast.style.display = "flex";
        toast.style.alignItems = "center";
        toast.style.gap = "8px";
        toast.style.transition = "all 0.3s cubic-bezier(0.16, 1, 0.3, 1)";
        toast.style.opacity = "0";
        toast.style.transform = "translateY(12px)";
        toast.style.color = "#ffffff";
        toast.style.fontWeight = "500";

        if (type === "success") {
            toast.style.backgroundColor = "#16a34a";
            toast.innerHTML = `<span>🟢</span> <b>LeetCode Lab:</b> ${safe}`;
        } else if (type === "warning") {
            toast.style.backgroundColor = "#d97706";
            toast.innerHTML = `<span>🟡</span> <b>LeetCode Lab:</b> ${safe}`;
        } else {
            toast.style.backgroundColor = "#dc2626";
            toast.innerHTML = `<span>🔴</span> <b>LeetCode Lab:</b> ${safe}`;
        }

        container.appendChild(toast);

        requestAnimationFrame(() => {
            toast.style.opacity = "1";
            toast.style.transform = "translateY(0)";
        });

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(12px)";
            setTimeout(() => toast.remove(), 300);
        }, CONFIG.TOAST_DURATION_MS);
    }

    // Listen for custom bridge events from page-context
    window.addEventListener("leetcode_lab_notification", (event) => {
        const { message, type } = event.detail || {};
        if (message) {
            showToast(message, type || "info");
        }
    });

    // =========================================================================
    // Page-Context Interceptor (Injected directly into page execution world)
    // =========================================================================
    function pageContextInterceptor() {
        // Double-injection guard: prevent re-running if page context already has our bridge.
        // LeetCode is a React SPA — DOMContentLoaded may fire multiple times during navigation.
        // The submission_id dedup set is the authoritative duplicate guard on the server side,
        // but we also prevent re-hooking fetch/XHR to avoid doubled POST requests.
        if (window.__leetcodeLabInstalled) {
            console.log("%c[LeetCode Lab Bridge]", "color: #10b981; font-weight: bold;", "Already installed — skipping re-injection.");
            return;
        }
        window.__leetcodeLabInstalled = true;

        const LOCAL_SERVER_INGEST = "http://127.0.0.1:8765/ingest";
        const processedSubmissions = new Set();
        const pendingSubmissions = new Map(); // submission_id -> { code, lang, question_id }

        // Save the original fetch NOW, before our hook replaces it.
        // Used internally so our GraphQL metadata calls don't pass through our own interceptor.
        const _rawFetch = window.fetch;

        function plog(...args) {
            console.log("%c[LeetCode Lab Bridge]", "color: #10b981; font-weight: bold;", ...args);
        }

        function pnotify(message, type = "success") {
            window.dispatchEvent(
                new CustomEvent("leetcode_lab_notification", {
                    detail: { message, type },
                })
            );
        }

        function getProblemSlug() {
            const match = window.location.pathname.match(/\/problems\/([a-z0-9-]+)/i);
            return match ? match[1].toLowerCase() : null;
        }

        // Fallback editor code extraction
        function getEditorSourceCode() {
            try {
                if (window.monaco && window.monaco.editor) {
                    const models = window.monaco.editor.getModels();
                    if (models && models.length > 0) {
                        for (const model of models) {
                            const val = model.getValue();
                            if (val && val.trim().length > 0) {
                                return val;
                            }
                        }
                    }
                }
            } catch (e) {}
            return null;
        }

        async function fetchProblemMetadata(slug) {
            const query = `
                query getQuestionDetail($titleSlug: String!) {
                    question(titleSlug: $titleSlug) {
                        questionFrontendId
                        title
                        difficulty
                        topicTags {
                            name
                            slug
                        }
                    }
                }
            `;
            try {
                // Use _rawFetch (the original, pre-hook fetch) so this GraphQL call
                // does not pass through our own submission interceptor.
                const res = await _rawFetch("https://leetcode.com/graphql", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ query, variables: { titleSlug: slug } }),
                });
                if (!res.ok) return null;
                const data = await res.json();
                const q = data?.data?.question;
                if (!q) return null;
                return {
                    problem_id: parseInt(q.questionFrontendId, 10),
                    title: q.title,
                    difficulty: q.difficulty,
                    leetcode_tags: (q.topicTags || []).map((t) => t.name),
                };
            } catch (e) {
                return null;
            }
        }

        async function sendToLocalhost(payload) {
            plog("Dispatching accepted payload to localhost:", payload.problem_id, payload.title, payload.language);
            try {
                const res = await window.fetch(LOCAL_SERVER_INGEST, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                const data = await res.json();
                if (res.ok && data.ok) {
                    plog("Successfully ingested into LeetCode Lab:", data);
                    pnotify(`Synced #${payload.problem_id} ${payload.title} (${payload.difficulty}) [${payload.language}]`, "success");
                } else {
                    console.error("[LeetCode Lab Bridge] Server rejected payload:", data);
                    pnotify(`Server Error: ${data.error || "Ingestion rejected"}`, "error");
                }
            } catch (err) {
                console.warn("[LeetCode Lab Bridge] Failed to connect to localhost server:", err);
                pnotify("Local server offline (run `python3 scripts/lab.py listen`)", "warning");
            }
        }

        async function handleAcceptedResult(submissionId, checkData) {
            if (processedSubmissions.has(submissionId)) {
                return;
            }

            const slug = getProblemSlug();
            if (!slug) {
                plog("No problem slug detected in pathname:", window.location.pathname);
                return;
            }

            plog("Handling Accepted submission ID:", submissionId, "for slug:", slug);

            const pending = pendingSubmissions.get(submissionId) || pendingSubmissions.get("latest") || {};
            const metadata = await fetchProblemMetadata(slug);

            if (!metadata || !metadata.problem_id) {
                pnotify(`Could not fetch metadata for problem '${slug}'`, "error");
                return;
            }

            let code = checkData.code || pending.code || getEditorSourceCode();
            let lang = checkData.lang || pending.lang || "cpp";

            if (!code) {
                pnotify("Accepted submission detected, but source code was missing", "error");
                return;
            }

            const payload = {
                submission_id: String(submissionId),
                problem_id: metadata.problem_id,
                slug: slug,
                title: metadata.title,
                difficulty: metadata.difficulty,
                language: lang,
                code: code,
                status: "Accepted",
                runtime: checkData.status_runtime || checkData.runtime || null,
                memory: checkData.status_memory || checkData.memory || null,
                leetcode_tags: metadata.leetcode_tags || [],
            };

            processedSubmissions.add(submissionId);
            await sendToLocalhost(payload);
        }

        // --- 1. Hook window.fetch ---
        // _rawFetch was captured at bridge initialization above.
        window.fetch = async function (...args) {
            const [resource, config] = args;
            const url = typeof resource === "string" ? resource : resource?.url || "";

            // Intercept submit request
            if (typeof url === "string" && (url.includes("/submit/") || url.includes("/submit"))) {
                try {
                    if (config && config.body) {
                        const body = JSON.parse(config.body);
                        plog("Intercepted submit fetch body:", body.lang, "question:", body.question_id);
                        pendingSubmissions.set("latest", {
                            code: body.typed_code,
                            lang: body.lang,
                            question_id: body.question_id,
                        });
                    }
                } catch (e) {}
            }

            const response = await _rawFetch.apply(this, args);

            // Intercept submit response
            if (typeof url === "string" && (url.includes("/submit/") || url.includes("/submit"))) {
                try {
                    const clone = response.clone();
                    clone.json().then((data) => {
                        if (data && data.submission_id) {
                            const subId = String(data.submission_id);
                            plog("Received submission_id via fetch:", subId);
                            const latest = pendingSubmissions.get("latest");
                            if (latest) {
                                pendingSubmissions.set(subId, latest);
                            }
                        }
                    }).catch(() => {});
                } catch (e) {}
            }

            // Intercept check/detail response
            if (typeof url === "string" && (url.includes("/check/") || url.includes("/detail/"))) {
                try {
                    const clone = response.clone();
                    clone.json().then((data) => {
                        if (data && (data.state === "SUCCESS" || data.status_msg)) {
                            const isAccepted = data.status_code === 10 || data.status_msg === "Accepted";
                            if (isAccepted) {
                                const subIdMatch = url.match(/detail\/(\d+)\//);
                                const subId = subIdMatch ? subIdMatch[1] : (data.submission_id ? String(data.submission_id) : "latest");
                                handleAcceptedResult(subId, data);
                            }
                        }
                    }).catch(() => {});
                } catch (e) {}
            }

            return response;
        };

        // --- 2. Hook window.XMLHttpRequest ---
        const rawXHR = window.XMLHttpRequest;
        const rawOpen = rawXHR.prototype.open;
        const rawSend = rawXHR.prototype.send;

        rawXHR.prototype.open = function (method, url, ...rest) {
            this._lab_url = url;
            this._lab_method = method;
            return rawOpen.apply(this, [method, url, ...rest]);
        };

        rawXHR.prototype.send = function (body) {
            const url = this._lab_url || "";
            if (typeof url === "string" && (url.includes("/submit/") || url.includes("/submit"))) {
                try {
                    if (body) {
                        const parsed = typeof body === "string" ? JSON.parse(body) : body;
                        plog("Intercepted submit XHR body:", parsed.lang);
                        pendingSubmissions.set("latest", {
                            code: parsed.typed_code,
                            lang: parsed.lang,
                            question_id: parsed.question_id,
                        });
                    }
                } catch (e) {}
            }

            this.addEventListener("load", function () {
                if (typeof url === "string" && (url.includes("/submit/") || url.includes("/submit"))) {
                    try {
                        const data = JSON.parse(this.responseText);
                        if (data && data.submission_id) {
                            const subId = String(data.submission_id);
                            plog("Received submission_id via XHR:", subId);
                            const latest = pendingSubmissions.get("latest");
                            if (latest) {
                                pendingSubmissions.set(subId, latest);
                            }
                        }
                    } catch (e) {}
                }

                if (typeof url === "string" && (url.includes("/check/") || url.includes("/detail/"))) {
                    try {
                        const data = JSON.parse(this.responseText);
                        if (data && (data.state === "SUCCESS" || data.status_msg)) {
                            const isAccepted = data.status_code === 10 || data.status_msg === "Accepted";
                            if (isAccepted) {
                                const subIdMatch = url.match(/detail\/(\d+)\//);
                                const subId = subIdMatch ? subIdMatch[1] : (data.submission_id ? String(data.submission_id) : "latest");
                                handleAcceptedResult(subId, data);
                            }
                        }
                    } catch (e) {}
                }
            });

            return rawSend.apply(this, [body]);
        };

        plog("Page-Context Bridge successfully installed. Monitoring submissions.");
    }

    // =========================================================================
    // Bridge Injection Helper
    // =========================================================================
    function injectBridge() {
        const script = document.createElement("script");
        script.id = "leetcode-lab-bridge";
        script.textContent = `(${pageContextInterceptor.toString()})();`;
        (document.head || document.documentElement).appendChild(script);
        script.remove();
        log("Injected page-context bridge into Main World.");
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", injectBridge);
    } else {
        injectBridge();
    }
})();
