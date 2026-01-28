import { useEffect, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dashboard, YoloModelPage, SettingsPage } from "@/pages";

// Global state untuk conversion status (tidak ter-cleanup saat ganti tab)
let globalConversionStatus: string | null = null;
let globalIsAdding = false;
const conversionStatusListeners = new Set<(status: string | null, isAdding: boolean) => void>();

export function useConversionStatus() {
  const [conversionStatus, setLocalStatus] = useState<string | null>(globalConversionStatus);
  const [isAdding, setLocalAdding] = useState(globalIsAdding);

  useEffect(() => {
    // Restore state saat component mount
    setLocalStatus(globalConversionStatus);
    setLocalAdding(globalIsAdding);

    // Register listener untuk update
    const listener = (status: string | null, adding: boolean) => {
      setLocalStatus(status);
      setLocalAdding(adding);
    };
    conversionStatusListeners.add(listener);

    return () => {
      conversionStatusListeners.delete(listener);
    };
  }, []);

  return { conversionStatus, isAdding };
}

export function updateConversionStatus(status: string | null, isAdding: boolean) {
  globalConversionStatus = status;
  globalIsAdding = isAdding;
  // Notify all listeners
  conversionStatusListeners.forEach((listener) => listener(status, isAdding));
}

export default function App() {
  useEffect(() => {
    // Setup global event listeners di App level (tidak ter-cleanup)
    let unlistenStart: (() => void) | null = null;
    let unlistenDone: (() => void) | null = null;
    let unlistenError: (() => void) | null = null;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    const setupListeners = async () => {
      unlistenStart = await listen<string>("model-conversion-start", (e) => {
        updateConversionStatus(e.payload, true);
      });
      unlistenDone = await listen<string>("model-conversion-done", (e) => {
        updateConversionStatus(e.payload, false);
        if (timeoutId) clearTimeout(timeoutId);
        timeoutId = setTimeout(() => updateConversionStatus(null, false), 3000);
      });
      unlistenError = await listen<string>("model-conversion-error", (e) => {
        updateConversionStatus(`Error: ${e.payload}`, false);
        if (timeoutId) clearTimeout(timeoutId);
        timeoutId = setTimeout(() => updateConversionStatus(null, false), 5000);
      });
    };

    setupListeners();

    return () => {
      if (unlistenStart) unlistenStart();
      if (unlistenDone) unlistenDone();
      if (unlistenError) unlistenError();
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b px-4 py-3">
        <h1 className="text-lg font-semibold">Palm Counting AI</h1>
      </header>
      <Tabs defaultValue="dashboard" className="w-full">
        <TabsList className="w-full justify-start rounded-none border-b bg-transparent p-0">
          <TabsTrigger value="dashboard" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent">
            Dashboard
          </TabsTrigger>
          <TabsTrigger value="yolo" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent">
            YOLO Model
          </TabsTrigger>
          <TabsTrigger value="settings" className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent">
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
    </div>
  );
}
