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

interface YoloModel {
  id: number;
  name: string;
  path: string;
  is_active: boolean;
}

export function YoloModelPage() {
  const [models, setModels] = useState<YoloModel[]>([]);

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
      multiple: false,
      filters: [{ name: "YOLO model", extensions: ["pt"] }],
    });
    if (!selected || typeof selected !== "string") return;
    try {
      await invoke("add_model_cmd", { sourcePath: selected, name: undefined });
      await load();
    } catch (e) {
      console.error(e);
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
          <Button onClick={addModel}>Add model</Button>
        </CardHeader>
        <CardContent>
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
