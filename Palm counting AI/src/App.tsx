import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dashboard, YoloModelPage, SettingsPage } from "@/pages";

export default function App() {
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
