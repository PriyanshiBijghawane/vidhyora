// CodePanel.jsx
/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import { useEffect, useRef, useState } from "react";
import {
  SandpackProvider,
  SandpackLayout,
  SandpackCodeEditor,
  SandpackPreview,
  SandpackFileExplorer,
  useSandpack,
} from "@codesandbox/sandpack-react";
import { dracula } from "@codesandbox/sandpack-themes";
import {
  Eye,
  Code2,
  Download,
  AlertTriangle,
  Bot,
  Loader2,
  ArrowUp,
} from "lucide-react";
import { RingLoader } from "react-spinners";
import JSZip from "jszip";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { PricingModal } from "@/components/PricingModal";
import { cn } from "@/lib/utils";

// ─── Tailwind / Entrypoint templates ──────────────────────────────────────────

const TAILWIND_HTML = `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Preview</title>
    <script id="tailwind-cdn" src="https://cdn.tailwindcss.com"></script>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>`;

const TAILWIND_INDEX_JS = `import React, { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import App from "./App";

function TailwindApp() {
  const [, setTick] = useState(0);

  useEffect(() => {
    if (typeof window !== "undefined" && window.tailwind) {
      return;
    }
    if (typeof document !== "undefined" && !document.getElementById("tailwind-cdn")) {
      const script = document.createElement("script");
      script.id = "tailwind-cdn";
      script.src = "https://cdn.tailwindcss.com";
      script.onload = () => {
        setTick((t) => t + 1);
      };
      document.head.appendChild(script);
    }
  }, []);

  return <App />;
}

const root = createRoot(document.getElementById("root"));
root.render(
  <StrictMode>
    <TailwindApp />
  </StrictMode>
);`;

const BASE_STYLES_CSS = `@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

*, ::before, ::after {
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 0;
  font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
`;

const TAILWIND_PACKAGE_JSON = JSON.stringify(
  {
    name: "vidhyora-preview",
    main: "/index.js",
    dependencies: {
      react: "^18.2.0",
      "react-dom": "^18.2.0",
    },
  },
  null,
  2
);

// ─── Placeholder ──────────────────────────────────────────────────────────────

const PLACEHOLDER_FILES = {
  "/App.js": {
    code: `export default function App() {
  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0a0a",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "system-ui, sans-serif",
    }}>
      <div style={{ textAlign: "center", color: "rgba(255,255,255,0.3)" }}>
        <div style={{ fontSize: 40, marginBottom: 16 }}>⚡</div>
        <p style={{ fontSize: 14 }}>Your app will appear here</p>
      </div>
    </div>
  );
}`,
  },
  "/index.js": { code: TAILWIND_INDEX_JS },
  "/public/index.html": { code: TAILWIND_HTML },
  "/index.html": { code: TAILWIND_HTML },
  "/styles.css": { code: BASE_STYLES_CSS },
  "/package.json": { code: TAILWIND_PACKAGE_JSON },
};

// ─── Base dependencies ────────────────────────────────────────────────────────

const BASE_DEPENDENCIES = {
  "lucide-react": "^0.344.0",
  clsx: "^2.1.0",
  "tailwind-merge": "^2.2.1",
};

function normalizeFiles(files) {
  if (!files || Object.keys(files).length === 0) return PLACEHOLDER_FILES;
  const normalized = {};
  for (const [rawPath, fObj] of Object.entries(files)) {
    const path = rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
    const code =
      typeof fObj === "object" && fObj !== null && "code" in fObj
        ? fObj.code
        : typeof fObj === "string"
        ? fObj
        : String(fObj ?? "");
    normalized[path] = { code };
  }
  if (!normalized["/App.js"]) {
    const alt =
      normalized["/App.jsx"] ||
      normalized["/App.tsx"] ||
      normalized["/src/App.js"] ||
      normalized["/src/App.jsx"];
    if (alt) {
      normalized["/App.js"] = alt;
    }
  }

  // Ensure entrypoint, HTML, styles, and package.json are configured for Tailwind
  if (!normalized["/index.js"]) {
    normalized["/index.js"] = { code: TAILWIND_INDEX_JS };
  }
  if (!normalized["/public/index.html"]) {
    normalized["/public/index.html"] = { code: TAILWIND_HTML };
  }
  if (!normalized["/index.html"]) {
    normalized["/index.html"] = { code: TAILWIND_HTML };
  }
  if (!normalized["/styles.css"]) {
    normalized["/styles.css"] = { code: BASE_STYLES_CSS };
  }
  if (!normalized["/package.json"]) {
    normalized["/package.json"] = { code: TAILWIND_PACKAGE_JSON };
  }

  return normalized;
}

// ─── SandpackInner ────────────────────────────────────────────────────────────

function SandpackInner({
  isGenerating,
  statusLog,
  activeTab,
  setActiveTab,
  onImprove,
  onFixError,
  fileData,
  appTitle,
  isImproving,
  isProUser,
}) {
  const { sandpack, listen } = useSandpack();
  const [previewError, setPreviewError] = useState(null);
  const [isExporting, setIsExporting] = useState(false);
  const [improveInput, setImproveInput] = useState("");
  const [showImproveInput, setShowImproveInput] = useState(false);
  const unsubscribeRef = useRef(null);

  // Push file content updates into Sandpack without flood compiling on mount
  const prevFilesRef = useRef(fileData?.files ?? {});
  useEffect(() => {
    if (!fileData?.files) return;
    const prev = prevFilesRef.current;
    for (const [rawPath, fObj] of Object.entries(fileData.files)) {
      const path = rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
      const code =
        typeof fObj === "object" && fObj !== null && "code" in fObj
          ? fObj.code
          : typeof fObj === "string"
          ? fObj
          : String(fObj ?? "");
      const prevObj = prev[rawPath] || prev[path];
      const prevCode =
        typeof prevObj === "object" && prevObj !== null && "code" in prevObj
          ? prevObj.code
          : typeof prevObj === "string"
          ? prevObj
          : undefined;
      if (prevCode !== undefined && prevCode !== code) {
        sandpack.updateFile(path, code, true);
      }
    }
    prevFilesRef.current = fileData.files;
  }, [fileData?.files, sandpack]);

  // Listen for Sandpack runtime errors
  useEffect(() => {
    unsubscribeRef.current = listen((msg) => {
      if (
        msg.type === "action" &&
        "action" in msg &&
        msg.action === "show-error"
      ) {
        const errMsg =
          "message" in msg && typeof msg.message === "string"
            ? msg.message
            : "An error occurred in the preview.";
        setPreviewError(errMsg);
        return;
      }
      if (msg.type === "compile") {
        const errMsg =
          "message" in msg && typeof msg.message === "string"
            ? msg.message
            : "Compile error in preview.";
        setPreviewError(errMsg);
        return;
      }
      if (msg.type === "success") {
        setPreviewError(null);
      }
    });
    return () => unsubscribeRef.current?.();
  }, [listen]);

  useEffect(() => {
    if (isGenerating) setPreviewError(null);
  }, [isGenerating]);

  const handleImproveSubmit = async () => {
    const trimmed = improveInput.trim();
    if (!trimmed || isImproving) return;
    setImproveInput("");
    setShowImproveInput(false);
    await onImprove(trimmed);
  };

  // ── Export to ZIP ──────────────────────────────────────────────────────────
  const handleExportZip = async () => {
    if (isExporting) return;
    setIsExporting(true);
    try {
      const filesToZip =
        Object.keys(sandpack.files).length > 0
          ? sandpack.files
          : fileData?.files ?? {};

      const dependencies = {
        ...BASE_DEPENDENCIES,
        ...(fileData?.dependencies ?? {}),
      };

      const zip = new JSZip();

      const packageJson = {
        name: "vidhyora-app",
        version: "1.0.0",
        private: true,
        dependencies: {
          react: "^18.2.0",
          "react-dom": "^18.2.0",
          "react-scripts": "5.0.1",
          ...dependencies,
        },
        scripts: {
          start: "react-scripts start",
          build: "react-scripts build",
        },
        browserslist: {
          production: [">0.2%", "not dead", "not op_mini all"],
          development: ["last 1 chrome version"],
        },
      };
      zip.file("package.json", JSON.stringify(packageJson, null, 2));

      zip.file(
        "public/index.html",
        `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Vidhyora App</title>
    <script src="https://cdn.tailwindcss.com"></script>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>`
      );

      for (const [filePath, fileObj] of Object.entries(filesToZip)) {
        if (filePath.startsWith("/node_modules/")) continue;
        if (
          filePath === "/index.html" ||
          filePath === "/public/index.html" ||
          filePath === "/index.js" ||
          filePath === "/styles.css" ||
          filePath === "/package.json"
        )
          continue;
        const code =
          typeof fileObj === "object" && fileObj !== null && "code" in fileObj
            ? fileObj.code
            : "";
        const zipPath = filePath.startsWith("/")
          ? `src${filePath}`
          : `src/${filePath}`;
        zip.file(zipPath, code);
      }

      zip.file(
        "src/index.js",
        `import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<React.StrictMode><App /></React.StrictMode>);`
      );

      zip.file(
        "README.md",
        `# Vidhyora App\n\nGenerated with [Vidhyora](https://vidhyora.app).\n\n## Getting started\n\n\`\`\`bash\nnpm install\nnpm start\n\`\`\``
      );

      const blob = await zip.generateAsync({ type: "blob" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const zipName = appTitle
        ? `${appTitle
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-|-$/g, "")}.zip`
        : "vidhyora-app.zip";
      a.download = zipName;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      setIsExporting(false);
    }
  };

  const currentStepLabel =
    statusLog[statusLog.length - 1]?.label ?? "Generating…";

  return (
    <Tabs
      value={activeTab}
      onValueChange={(v) => setActiveTab(v)}
      className="flex h-full flex-1 flex-col gap-0 overflow-hidden"
    >
      {/* Tabs + Actions bar */}
      <div className="flex items-center justify-between border-b border-white/6 px-2 shrink-0">
        <TabsList
          variant="line"
          className="h-auto gap-0 rounded-none bg-transparent p-0"
        >
          <TabsTrigger className="border-b-2 pt-2" value="code">
            <Code2 className="h-3.5 w-3.5" />
            Code
          </TabsTrigger>
          <TabsTrigger className="border-b-2 pt-2" value="preview">
            <Eye className="h-3.5 w-3.5" />
            Preview
          </TabsTrigger>
        </TabsList>

        <div className="flex items-center gap-1.5">
          {/* ── Improve button ── */}
          {isProUser ? (
            showImproveInput ? (
              <div className="flex items-center gap-1.5">
                <div className="relative flex items-center">
                  <Bot className="pointer-events-none absolute left-2.5 h-3.5 w-3.5 text-violet-400" />
                  <input
                    autoFocus
                    value={improveInput}
                    onChange={(e) => setImproveInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleImproveSubmit();
                      if (e.key === "Escape") setShowImproveInput(false);
                    }}
                    placeholder="What should I improve?"
                    className="h-7 w-56 rounded-md border border-violet-500/30 bg-gradient-to-r from-violet-500/10 via-fuchsia-500/10 to-cyan-500/10 pl-8 pr-3 text-xs text-white/80 placeholder:text-white/30 focus:border-violet-400/50 focus:outline-none focus:shadow-[0_0_10px_rgba(139,92,246,0.2)]"
                  />
                </div>
                <button
                  onClick={handleImproveSubmit}
                  disabled={!improveInput.trim() || isImproving}
                  className="group relative flex h-7 w-7 items-center justify-center overflow-hidden rounded-md border border-violet-500/30 bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20 text-violet-300 transition-all duration-200 hover:border-violet-400/50 hover:from-violet-500/30 hover:to-fuchsia-500/30 hover:shadow-[0_0_10px_rgba(139,92,246,0.3)] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {isImproving ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <ArrowUp className="h-3 w-3" />
                  )}
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowImproveInput(true)}
                disabled={isImproving || !fileData}
                className="group relative flex h-7 cursor-pointer items-center gap-1.5 overflow-hidden rounded-md border border-white/10 bg-gradient-to-r from-violet-500/10 via-fuchsia-500/10 to-cyan-500/10 px-2.5 text-xs font-medium transition-all duration-300 hover:border-white/20 hover:from-violet-500/20 hover:via-fuchsia-500/20 hover:to-cyan-500/20 hover:shadow-[0_0_12px_rgba(139,92,246,0.3)] disabled:cursor-not-allowed disabled:opacity-40"
              >
                <span className="pointer-events-none absolute inset-0 -translate-x-full animate-[shimmer_2.5s_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent" />
                {isImproving ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-400" />
                ) : (
                  <Bot className="h-3.5 w-3.5 text-violet-400 transition-colors group-hover:text-violet-300" />
                )}
                <span className="bg-gradient-to-r from-violet-300 via-fuchsia-300 to-cyan-300 bg-clip-text text-transparent">
                  {isImproving ? "Improving…" : "Improve with Agent"}
                </span>
                {!isImproving && (
                  <span className="rounded-sm bg-violet-500/30 px-1 py-0.5 text-[10px] font-semibold leading-none text-violet-300">
                    PRO
                  </span>
                )}
              </button>
            )
          ) : (
            <PricingModal reason="upgrade">
              <span className="group relative flex h-7 cursor-pointer items-center gap-1.5 overflow-hidden rounded-md border border-white/10 bg-gradient-to-r from-violet-500/10 via-fuchsia-500/10 to-cyan-500/10 px-2.5 text-xs font-medium text-white/60 transition-all duration-300 hover:border-white/20 hover:from-violet-500/20 hover:via-fuchsia-500/20 hover:to-cyan-500/20 hover:text-white/90 hover:shadow-[0_0_12px_rgba(139,92,246,0.3)]">
                <span className="pointer-events-none absolute inset-0 -translate-x-full animate-[shimmer_2.5s_infinite] bg-gradient-to-r from-transparent via-white/10 to-transparent" />
                <Bot className="h-3.5 w-3.5 text-violet-400 transition-colors group-hover:text-violet-300" />
                <span className="bg-gradient-to-r from-violet-300 via-fuchsia-300 to-cyan-300 bg-clip-text text-transparent">
                  Improve with Agent
                </span>
                <span className="rounded-sm bg-violet-500/30 px-1 py-0.5 text-[10px] font-semibold leading-none text-violet-300">
                  PRO
                </span>
              </span>
            </PricingModal>
          )}

          <Button
            variant="ghost"
            onClick={handleExportZip}
            disabled={isExporting || !fileData}
          >
            {isExporting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5" />
            )}
            Download
          </Button>
        </div>
      </div>

      {/* Content area */}
      <div className="relative flex-1 overflow-hidden h-full min-h-0 w-full">
        {(isGenerating || isImproving) && (
          <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-6 bg-[#0a0a0a]/85 backdrop-blur-sm">
            <RingLoader color="#60a5fa" size={64} speedMultiplier={0.8} />
            <div className="flex flex-col items-center gap-1.5">
              <p className="text-sm font-medium text-white/60">
                {isImproving ? "Improving with Cline AI…" : currentStepLabel}
              </p>
              <p className="text-xs text-white/20">
                This usually takes 10–20 seconds
              </p>
            </div>
          </div>
        )}

        <style>{`
          .sp-wrapper {
            height: 100% !important;
            width: 100% !important;
          }
          .sp-preview,
          .sp-preview-container,
          .sp-preview-iframe,
          .sp-preview iframe {
            height: 100% !important;
            min-height: 100% !important;
            max-height: 100% !important;
            width: 100% !important;
            flex: 1 !important;
          }
        `}</style>

        {/* Preview Panel */}
        <div
          className={cn(
            "h-full w-full flex flex-col",
            activeTab === "preview" ? "flex" : "hidden"
          )}
        >
          <SandpackPreview
            style={{ height: "100%", width: "100%", flex: 1 }}
            showOpenInCodeSandbox={false}
            showRefreshButton={true}
            showRestartButton={true}
          />
        </div>

        {/* Code Panel */}
        <div
          className={cn(
            "h-full w-full",
            activeTab === "code" ? "flex" : "hidden"
          )}
        >
          <SandpackFileExplorer
            style={{
              height: "100%",
              width: "180px",
              borderRight: "0.5px solid rgba(255,255,255,0.08)",
            }}
          />
          <SandpackCodeEditor
            style={{ height: "100%", flex: 1 }}
            showTabs
            showLineNumbers
            showInlineErrors
            closableTabs
            readOnly
          />
        </div>
      </div>

      {/* Preview error banner — uses onFixError (Gemini), not onImprove (Cline) */}
      {previewError &&
        !isGenerating &&
        !isImproving &&
        activeTab === "preview" && (
          <div className="absolute inset-x-0 -bottom-3 z-20 border-t border-red-500/20 bg-red-950/99 p-4 pb-6">
            <div className="flex items-center gap-2.5">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-400/70" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-red-400/80">
                  Preview error
                </p>
                <p className="break-all text-[11px] text-red-300/50">
                  {previewError}
                </p>
              </div>
              <Button
                onClick={() => onFixError(previewError)}
                variant="destructive"
              >
                <Bot className="h-3 w-3" />
                Fix with AI
              </Button>
            </div>
          </div>
        )}
    </Tabs>
  );
}

// ─── CodePanel (outer) ────────────────────────────────────────────────────────

export function CodePanel({
  fileData,
  isGenerating,
  statusLog,
  onImprove,
  onFixError,
  onFilePatch: _onFilePatch,
  appTitle,
  isImproving,
  isProUser,
  workspaceError,
  requestedWorkspaceId,
}) {
  const [activeTab, setActiveTab] = useState("preview");

  useEffect(() => {
    if (fileData) setActiveTab("preview");
  }, [fileData]);

  if (workspaceError) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center h-full p-8 text-center bg-[#0a0a0a] select-none">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-red-500/10 text-red-400 mb-4 ring-1 ring-red-500/20">
          <AlertTriangle className="h-7 w-7 text-red-400" />
        </div>
        <h2 className="text-lg font-semibold text-white tracking-tight mb-2">
          {workspaceError.code === "NOT_FOUND"
            ? "Workspace Not Found"
            : workspaceError.code === "UNAUTHORIZED"
            ? "Access Denied"
            : "Failed to Load Workspace"}
        </h2>
        <p className="text-sm text-white/50 max-w-md mb-3 leading-relaxed">
          {workspaceError.message}
        </p>
        {requestedWorkspaceId && (
          <div className="flex items-center gap-2 mb-6">
            <span className="text-[11px] uppercase tracking-wider text-white/30 font-medium">Workspace ID</span>
            <code className="text-xs font-mono text-white/60 bg-white/5 border border-white/10 px-2.5 py-1 rounded-md">
              {requestedWorkspaceId}
            </code>
          </div>
        )}
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            className="border-white/10 hover:bg-white/5 text-white/80 text-xs h-9 px-4 cursor-pointer"
            onClick={() => window.location.reload()}
          >
            Retry
          </Button>
          <Button
            variant="secondary"
            className="bg-white/10 hover:bg-white/15 text-white text-xs h-9 px-4 cursor-pointer"
            onClick={() => (window.location.href = "/projects")}
          >
            Back to Projects
          </Button>
          <Button
            variant="ghost"
            className="text-white/60 hover:text-white text-xs h-9 px-4 cursor-pointer"
            onClick={() => (window.location.href = "/workspace")}
          >
            New Workspace
          </Button>
        </div>
      </div>
    );
  }

  const files = normalizeFiles(fileData?.files);
  const dependencies = {
    ...BASE_DEPENDENCIES,
    ...(fileData?.dependencies ?? {}),
  };

  // Key on appTitle + file paths so reopening a saved project mounts cleanly
  // without reusing stale aborted bundler state.
  const filePathKey = `${appTitle ?? "app"}_${Object.keys(files).sort().join("|")}`;

  return (
    <div className="flex flex-1 flex-col overflow-hidden h-full">
      <SandpackProvider
        key={filePathKey}
        template="react"
        theme={dracula}
        files={files}
        customSetup={{ dependencies }}
        className="flex flex-1 flex-col h-full w-full !h-full !w-full"
        style={{ height: "100%", width: "100%" }}
        options={{
          bundlerURL:
            process.env.NEXT_PUBLIC_SANDPACK_BUNDLER_URL ||
            "https://sandpack-bundler.codesandbox.io",
          initMode: "immediate",
          externalResources: ["https://cdn.tailwindcss.com"],
          recompileMode: "immediate",
          recompileDelay: 300,
          bundlerTimeOut: 90000,
          activeFile: "/App.js",
          visibleFiles: fileData?.files
            ? Object.keys(fileData.files).map((p) =>
                p.startsWith("/") ? p : `/${p}`
              )
            : ["/App.js"],
        }}
      >
        <SandpackInner
          isGenerating={isGenerating}
          statusLog={statusLog}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          onImprove={onImprove}
          onFixError={onFixError}
          fileData={fileData}
          appTitle={appTitle}
          isImproving={isImproving}
          isProUser={isProUser}
        />
      </SandpackProvider>
    </div>
  );
}
