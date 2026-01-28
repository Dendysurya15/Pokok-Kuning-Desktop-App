import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";

interface SystemSpecs {
  os: string;
  processor: string;
  total_ram_gb: string;
  gpu: string;
  gpu_memory: string;
  cpu_cores: number;
  cpu_threads: number;
}

interface YoloModel {
  id: number;
  name: string;
  path: string;
  is_active: boolean;
}

interface AppConfig {
  imgsz?: string;
  iou?: string;
  conf?: string;
  device?: string;
  convert_kml?: string;
  convert_shp?: string;
  save_annotated?: string;
  last_folder_path?: string;
}

interface ProgressPayload {
  processed: number;
  total: number;
  current_file: string;
  status: string;
  abnormal_count: number;
  normal_count: number;
}

export function Dashboard() {
  const [folder, setFolder] = useState("");
  const [models, setModels] = useState<YoloModel[]>([]);
  const [activeModelId, setActiveModelId] = useState<string>("");
  const [, setConfig] = useState<AppConfig>({});
  const [specs, setSpecs] = useState<SystemSpecs | null>(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<ProgressPayload | null>(null);
  const [log, setLog] = useState<string[]>([]);

  const load = useCallback(async () => {
    try {
      const [s, c, m] = await Promise.all([
        invoke<SystemSpecs>("get_specs"),
        invoke<AppConfig>("load_config_cmd").catch(() => ({})),
        invoke<YoloModel[]>("list_models_cmd").catch(() => []),
      ]);
      setSpecs(s);
      setConfig(c);
      setModels(m);
      const active = m.find((x) => x.is_active);
      setActiveModelId(active ? String(active.id) : "");
      const cfg = c as AppConfig;
      if (cfg?.last_folder_path) setFolder(cfg.last_folder_path);
    } catch (e) {
      setLog((prev) => [...prev, `Error: ${e}`]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const unlistenLog = listen<string>("processing-log", (e) =>
      setLog((prev) => [...prev, e.payload])
    );
    const unlistenProg = listen<ProgressPayload>("processing-progress", (e) =>
      setProgress(e.payload)
    );
    const unlistenDone = listen("processing-done", () => {
      setRunning(false);
      setProgress(null);
      load();
    });
    return () => {
      unlistenLog.then((u) => u());
      unlistenProg.then((u) => u());
      unlistenDone.then((u) => u());
    };
  }, [load]);

  const pickFolder = async () => {
    const selected = await open({ directory: true, multiple: false });
    if (!selected || typeof selected !== "string") return;
    setFolder(selected);
    try {
      const c = await invoke<AppConfig>("load_config_cmd").catch(() => ({}));
      await invoke("save_config_cmd", { c: { ...c, last_folder_path: selected } });
    } catch {
      /* ignore */
    }
  };

  const run = async () => {
    if (!folder || !activeModelId) {
      setLog((prev) => [...prev, "Select folder and an active model first."]);
      return;
    }
    setRunning(true);
    setLog((prev) => [...prev, "Starting processing..."]);
    setProgress(null);
    try {
      await invoke("run_processing_cmd", { folder });
    } catch (e) {
      setLog((prev) => [...prev, `Error: ${e}`]);
      setRunning(false);
    }
  };

  const cancel = () => invoke("cancel_processing");

  const clearLog = () => setLog([]);

  return (
    <div className="space-y-4 p-4">
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {specs && (
              <>
                <p>OS: {specs.os}</p>
                <p>CPU: {specs.cpu_cores}C / {specs.cpu_threads}T</p>
                <p>RAM: {specs.total_ram_gb}</p>
                <p>
                  GPU:{" "}
                  <Badge variant={specs.gpu.includes("No") ? "destructive" : "default"}>
                    {specs.gpu} {specs.gpu_memory}
                  </Badge>
                </p>
              </>
            )}
            <p>Folder: {folder || "—"}</p>
            <p>Process: {running ? "Running" : "Idle"}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>File &amp; Model</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Folder</Label>
              <div className="flex gap-2">
                <Input
                  readOnly
                  value={folder}
                  placeholder="Select folder with images + .tfw"
                />
                <Button variant="outline" onClick={pickFolder} disabled={running}>
                  Browse
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label>YOLO Model</Label>
              <Select
                value={activeModelId}
                onValueChange={(v) => {
                  setActiveModelId(v);
                  invoke("set_active_model_cmd", { id: Number(v) });
                }}
                disabled={running}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent>
                  {models.map((m) => (
                    <SelectItem key={m.id} value={String(m.id)}>
                      {m.name} {m.is_active ? "(active)" : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2">
              <Button onClick={run} disabled={running || !folder || !activeModelId}>
                Run processing
              </Button>
              {running && (
                <Button variant="destructive" onClick={cancel}>
                  Cancel
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {progress && (
        <Card>
          <CardHeader>
            <CardTitle>Progress</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Progress value={(progress.processed / progress.total) * 100} />
            <p className="text-sm">
              {progress.processed} / {progress.total} — {progress.current_file} —{" "}
              {progress.status}
            </p>
            <p className="text-sm text-muted-foreground">
              Abnormal: {progress.abnormal_count} — Normal: {progress.normal_count}
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Log</CardTitle>
          <Button variant="ghost" size="sm" onClick={clearLog}>
            Clear
          </Button>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-48 rounded border p-2 font-mono text-xs">
            {log.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
