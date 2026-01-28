import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";

interface AppConfig {
  imgsz?: string;
  iou?: string;
  conf?: string;
  device?: string;
  max_det?: string;
  line_width?: string;
  convert_kml?: string;
  convert_shp?: string;
  save_annotated?: string;
  show_labels?: string;
  show_conf?: string;
}

export function SettingsPage() {
  const [config, setConfig] = useState<AppConfig>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    invoke<AppConfig>("load_config_cmd")
      .then(setConfig)
      .catch(() => {});
  }, []);

  const update = (k: keyof AppConfig, v: string | undefined) =>
    setConfig((c) => ({ ...c, [k]: v }));

  const save = async () => {
    try {
      await invoke("save_config_cmd", { c: config });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-4 p-4 max-w-2xl">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Processing settings</CardTitle>
          <Button onClick={save}>{saved ? "Saved" : "Save"}</Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Image size (imgsz)</Label>
              <Input
                value={config.imgsz ?? "12800"}
                onChange={(e) => update("imgsz", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Confidence</Label>
              <Input
                value={config.conf ?? "0.2"}
                onChange={(e) => update("conf", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>IOU</Label>
              <Input
                value={config.iou ?? "0.2"}
                onChange={(e) => update("iou", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Max detections</Label>
              <Input
                value={config.max_det ?? "10000"}
                onChange={(e) => update("max_det", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Line width</Label>
              <Input
                value={config.line_width ?? "3"}
                onChange={(e) => update("line_width", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Device</Label>
              <Input
                value={config.device ?? "auto"}
                onChange={(e) => update("device", e.target.value)}
                placeholder="auto | cpu | cuda"
              />
            </div>
          </div>
          <div className="flex flex-wrap gap-6">
            <label className="flex items-center gap-2">
              <Checkbox
                checked={config.convert_kml === "true"}
                onCheckedChange={(c) =>
                  update("convert_kml", c ? "true" : "false")
                }
              />
              <span>Convert KML</span>
            </label>
            <label className="flex items-center gap-2">
              <Checkbox
                checked={config.convert_shp !== "false"}
                onCheckedChange={(c) =>
                  update("convert_shp", c ? "true" : "false")
                }
              />
              <span>Convert Shapefile</span>
            </label>
            <label className="flex items-center gap-2">
              <Checkbox
                checked={config.save_annotated !== "false"}
                onCheckedChange={(c) =>
                  update("save_annotated", c ? "true" : "false")
                }
              />
              <span>Save annotated images</span>
            </label>
            <label className="flex items-center gap-2">
              <Checkbox
                checked={config.show_labels !== "false"}
                onCheckedChange={(c) =>
                  update("show_labels", c ? "true" : "false")
                }
              />
              <span>Show labels</span>
            </label>
            <label className="flex items-center gap-2">
              <Checkbox
                checked={config.show_conf === "true"}
                onCheckedChange={(c) =>
                  update("show_conf", c ? "true" : "false")
                }
              />
              <span>Show confidence</span>
            </label>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
