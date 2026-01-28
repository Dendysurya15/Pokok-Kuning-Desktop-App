import { useEffect } from "react";
import { listen } from "@tauri-apps/api/event";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Dashboard, YoloModelPage, SettingsPage } from "@/pages";
import { useConversionStore } from "@/stores/conversion";
import {
  useProcessingStore,
  type ProcessingProgress,
} from "@/stores/processing";

function ProcessingStrip() {
  const running = useProcessingStore((s) => s.running);
  const progress = useProcessingStore((s) => s.progress);
  const log = useProcessingStore((s) => s.log);
  const clearLog = useProcessingStore((s) => s.clearLog);
  const cancel = useProcessingStore((s) => s.cancel);

  if (!running) return null;
  return (
    <div className="border-t bg-muted/30 space-y-4 p-4">
      <div className="flex items-center justify-between gap-4">
        <span className="text-sm font-medium">Processing…</span>
        <Button variant="destructive" size="sm" onClick={cancel}>
          Cancel
        </Button>
      </div>
      {progress && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Progress value={(progress.processed / progress.total) * 100} />
            <p className="text-sm">
              {progress.processed} / {progress.total} —{" "}
              {progress.current_file?.split(/[/\\]/).pop() ?? progress.current_file}{" "}
              — {progress.status}
            </p>
            <p className="text-sm text-muted-foreground">
              Abnormal: {progress.abnormal_count} — Normal:{" "}
              {progress.normal_count}
            </p>
          </CardContent>
        </Card>
      )}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-2">
          <CardTitle className="text-base">Log</CardTitle>
          <Button variant="ghost" size="sm" onClick={clearLog}>
            Clear
          </Button>
        </CardHeader>
        <CardContent className="py-2">
          <ScrollArea className="h-40 rounded border p-2 font-mono text-xs">
            {log.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}

export default function App() {
  useEffect(() => {
    const unsubs: (() => void)[] = [];
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    const setConversion = useConversionStore.getState().setStatus;

    const setup = async () => {
      let u = await listen<string>("model-conversion-start", (e) => {
        setConversion(e.payload, true);
      });
      if (cancelled) {
        u();
        return;
      }
      unsubs.push(u);

      u = await listen<string>("model-conversion-done", (e) => {
        setConversion(e.payload, false);
        if (timeoutId) clearTimeout(timeoutId);
        timeoutId = setTimeout(() => setConversion(null, false), 3000);
      });
      if (cancelled) {
        u();
        return;
      }
      unsubs.push(u);

      u = await listen<string>("model-conversion-error", (e) => {
        setConversion(`Error: ${e.payload}`, false);
        if (timeoutId) clearTimeout(timeoutId);
        timeoutId = setTimeout(() => setConversion(null, false), 5000);
      });
      if (cancelled) {
        u();
        return;
      }
      unsubs.push(u);
    };
    setup();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
      unsubs.forEach((f) => f());
    };
  }, []);

  useEffect(() => {
    const unsubs: (() => void)[] = [];
    let cancelled = false;
    const appendLog = useProcessingStore.getState().appendLog;
    const setProgress = useProcessingStore.getState().setProgress;
    const setRunning = useProcessingStore.getState().setRunning;

    const setup = async () => {
      let u = await listen<string>("processing-log", (e) =>
        appendLog(e.payload)
      );
      if (cancelled) {
        u();
        return;
      }
      unsubs.push(u);

      u = await listen<ProcessingProgress>(
        "processing-progress",
        (e) => setProgress(e.payload)
      );
      if (cancelled) {
        u();
        return;
      }
      unsubs.push(u);

      u = await listen("processing-done", () => setRunning(false));
      if (cancelled) {
        u();
        return;
      }
      unsubs.push(u);
    };
    setup();

    return () => {
      cancelled = true;
      unsubs.forEach((f) => f());
    };
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b px-4 py-3">
        <h1 className="text-lg font-semibold">Palm Counting AI</h1>
      </header>
      <Tabs defaultValue="dashboard" className="w-full">
        <TabsList className="w-full justify-start rounded-none border-b bg-transparent p-0">
          <TabsTrigger
            value="dashboard"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            Dashboard
          </TabsTrigger>
          <TabsTrigger
            value="yolo"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            YOLO Model
          </TabsTrigger>
          <TabsTrigger
            value="settings"
            className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
          >
            Settings
          </TabsTrigger>
        </TabsList>
        <TabsContent value="dashboard">
          <Dashboard />
        </TabsContent>
        <TabsContent value="yolo">
          <YoloModelPage />
        </TabsContent>
        <TabsContent value="settings">
          <SettingsPage />
        </TabsContent>
      </Tabs>
      <ProcessingStrip />
      <footer className="border-t px-4 py-2 text-center text-xs text-muted-foreground">
        © 2026–present Digital Architect. All rights reserved.
      </footer>
    </div>
  );
}
