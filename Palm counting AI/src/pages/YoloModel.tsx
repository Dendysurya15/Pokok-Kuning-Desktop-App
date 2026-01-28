import { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Loader2 } from "lucide-react";
import { useConversionStatus, updateConversionStatus } from "@/App";

interface YoloModel {
  id: number;
  name: string;
  path: string;
  is_active: boolean;
}

export function YoloModelPage() {
  const [models, setModels] = useState<YoloModel[]>([]);
  const { conversionStatus, isAdding } = useConversionStatus();

  const load = useCallback(async () => {
    try {
      const m = await invoke<YoloModel[]>("list_models_cmd");
      setModels(m);
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const addModel = async () => {
    const selected = await open({
      multiple: true,  // Enable multiple file selection
      filters: [{ name: "YOLO model", extensions: ["pt", "onnx"] }],
    });
    if (!selected) return;
    
    // Handle both single and multiple selection
    const files = Array.isArray(selected) ? selected : [selected];
    if (files.length === 0) return;
    
    updateConversionStatus(null, true);
    
    try {
      if (files.length === 1) {
        // Single file - use existing command
        await invoke("add_model_cmd", { sourcePath: files[0], name: undefined });
      } else {
        // Multiple files - use new command
        await invoke("add_models_cmd", { sourcePaths: files });
      }
      await load();
    } catch (e) {
      console.error(e);
      updateConversionStatus(`Error: ${e}`, false);
      setTimeout(() => updateConversionStatus(null, false), 5000);
    } finally {
      // Don't immediately clear status for multiple files - let the final summary show
      if (files.length === 1) {
        updateConversionStatus(null, false);
      } else {
        // For multiple files, wait a bit longer to show final summary
        setTimeout(() => updateConversionStatus(null, false), 3000);
      }
    }
  };

  const remove = async (id: number) => {
    try {
      await invoke("remove_model_cmd", { id });
      await load();
    } catch (e) {
      console.error(e);
    }
  };

  const setActive = async (id: number) => {
    try {
      await invoke("set_active_model_cmd", { id });
      await load();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-4 p-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>YOLO Model Library</CardTitle>
          <Button onClick={addModel} disabled={isAdding}>
            {isAdding ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Adding...
              </>
            ) : (
              "Add model"
            )}
          </Button>
        </CardHeader>
        <CardContent>
          {conversionStatus && (
            <div className={`mb-4 rounded-md p-3 ${
              conversionStatus.startsWith("Error") 
                ? "bg-destructive/10 border border-destructive/20" 
                : conversionStatus.includes("Successfully")
                ? "bg-green-500/10 border border-green-500/20"
                : "bg-muted"
            }`}>
              <div className="flex items-center gap-2">
                {isAdding && <Loader2 className="h-4 w-4 animate-spin" />}
                <p className={`text-sm ${
                  conversionStatus.startsWith("Error") 
                    ? "text-destructive" 
                    : conversionStatus.includes("Successfully")
                    ? "text-green-600"
                    : ""
                }`}>
                  {conversionStatus}
                </p>
              </div>
              {isAdding && (
                <Progress value={undefined} className="mt-2" />
              )}
            </div>
          )}
          {models.length === 0 ? (
            <p className="text-muted-foreground">No models. Add a .pt file.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Path</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead className="w-[200px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {models.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell>{m.name}</TableCell>
                    <TableCell className="max-w-[300px] truncate font-mono text-xs">
                      {m.path}
                    </TableCell>
                    <TableCell>
                      {m.is_active ? (
                        <Badge>Active</Badge>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setActive(m.id)}
                        >
                          Set default
                        </Button>
                      )}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => remove(m.id)}
                      >
                        Remove
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
