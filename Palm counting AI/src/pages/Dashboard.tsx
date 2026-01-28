import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { openPath } from "@tauri-apps/plugin-opener";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { FolderOpen, Trash2 } from "lucide-react";
import { useProcessingStore } from "@/stores/processing";

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

interface TiffEntry {
  path: string;
  checked: boolean;
}

export function Dashboard() {
  const running = useProcessingStore((s) => s.running);
  const outputFolders = useProcessingStore((s) => s.outputFolders);
  const startProcessing = useProcessingStore((s) => s.start);
  const setRunning = useProcessingStore((s) => s.setRunning);
  const appendLog = useProcessingStore((s) => s.appendLog);

  const [tiffList, setTiffList] = useState<TiffEntry[]>([]);
  const [models, setModels] = useState<YoloModel[]>([]);
  const [activeModelId, setActiveModelId] = useState<string>("");
  const [, setConfig] = useState<AppConfig>({});
  const [specs, setSpecs] = useState<SystemSpecs | null>(null);

  const load = useCallback(async () => {
    try {
      const [s, c, m, tiffPaths] = await Promise.all([
        invoke<SystemSpecs>("get_specs"),
        invoke<AppConfig>("load_config_cmd").catch(() => ({})),
        invoke<YoloModel[]>("list_models_cmd").catch(() => []),
        invoke<string[]>("list_tiff_paths_cmd").catch(() => []),
      ]);
      setSpecs(s);
      setConfig(c);
      setModels(m);
      const active = m.find((x) => x.is_active);
      setActiveModelId(active ? String(active.id) : "");
      setTiffList(
        (tiffPaths as string[]).map((path) => ({ path, checked: false }))
      );
    } catch (e) {
      appendLog(`Error: ${e}`);
    }
  }, [appendLog]);

  useEffect(() => {
    load();
  }, [load]);

  const pickTiff = async () => {
    const selected = await open({
      multiple: true,
      filters: [{ name: "TIFF", extensions: ["tif", "tiff"] }],
    });
    if (!selected) return;
    const files = Array.isArray(selected) ? selected : [selected];
    const existing = new Set(tiffList.map((t) => t.path));
    const toAdd = files.filter((p) => !existing.has(p));
    if (toAdd.length === 0) return;
    try {
      await invoke("add_tiff_paths_cmd", { paths: toAdd });
      const added: TiffEntry[] = toAdd.map((path) => ({ path, checked: false }));
      setTiffList((prev) => [...prev, ...added]);
    } catch (e) {
      appendLog(`Error saving TIFF list: ${e}`);
    }
  };

  const removeTiff = async (path: string) => {
    if (running) return;
    try {
      await invoke("remove_tiff_path_cmd", { path });
      setTiffList((prev) => prev.filter((t) => t.path !== path));
    } catch (e) {
      appendLog(`Error removing: ${e}`);
    }
  };

  const setChecked = (path: string, checked: boolean) => {
    setTiffList((prev) =>
      prev.map((t) => (t.path === path ? { ...t, checked } : t))
    );
  };

  const selectAll = (checked: boolean) => {
    setTiffList((prev) => prev.map((t) => ({ ...t, checked })));
  };

  const checkedCount = tiffList.filter((t) => t.checked).length;
  const allChecked = tiffList.length > 0 && checkedCount === tiffList.length;
  const someChecked = checkedCount > 0;

  const run = async () => {
    const active = models.find((m) => String(m.id) === activeModelId);
    const modelName = active?.name ?? "";
    if (!modelName) {
      appendLog("Select an active YOLO model first.");
      return;
    }
    const toProcess = tiffList.filter((t) => t.checked).map((t) => t.path);
    if (toProcess.length === 0) {
      appendLog("Select at least one TIFF (checkbox) to process.");
      return;
    }
    startProcessing();
    try {
      await invoke("run_processing_cmd", { files: toProcess, modelName });
    } catch (e) {
      appendLog(`Error: ${e}`);
      setRunning(false);
    }
  };

  const openResultFolder = (path: string) => {
    const out = outputFolders[path];
    if (out) openPath(out);
  };

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
                  <Badge
                    variant={
                      specs.gpu.includes("No") ? "destructive" : "default"
                    }
                  >
                    {specs.gpu} {specs.gpu_memory}
                  </Badge>
                </p>
              </>
            )}
            <p>TIFF files: {tiffList.length}</p>
            <p>Process: {running ? "Running" : "Idle"}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>File &amp; Model</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>TIFF files</Label>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={pickTiff}
                  disabled={running}
                >
                  Pick TIFF
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
            {tiffList.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="select-all"
                    checked={allChecked}
                    onCheckedChange={(c) => selectAll(!!c)}
                    disabled={running}
                  />
                  <Label
                    htmlFor="select-all"
                    className="text-sm font-normal cursor-pointer"
                  >
                    Select all ({checkedCount} selected)
                  </Label>
                </div>
                <ScrollArea className="h-32 rounded border p-2">
                  <div className="space-y-1.5">
                    {tiffList.map((t) => (
                      <div
                        key={t.path}
                        className="flex items-center gap-2 text-sm"
                      >
                        <Checkbox
                          checked={t.checked}
                          onCheckedChange={(c) => setChecked(t.path, !!c)}
                          disabled={running}
                        />
                        <span
                          className="flex-1 truncate font-mono"
                          title={t.path}
                        >
                          {t.path.split(/[/\\]/).pop() ?? t.path}
                        </span>
                        {outputFolders[t.path] && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="shrink-0 h-7 px-2"
                            onClick={() => openResultFolder(t.path)}
                            title="Open result folder"
                          >
                            <FolderOpen className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="shrink-0 h-7 px-2 text-muted-foreground hover:text-destructive"
                          onClick={() => removeTiff(t.path)}
                          disabled={running}
                          title="Remove from list"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            )}
            <div className="flex gap-2">
              <Button
                onClick={run}
                disabled={running || !activeModelId || !someChecked}
              >
                Run processing
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
