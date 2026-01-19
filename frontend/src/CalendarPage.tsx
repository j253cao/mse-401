import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Calendar, Construction } from "lucide-react";

export default function CalendarPage() {
  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4">
      <Card className="glass-card max-w-md w-full">
        <CardContent className="py-16 text-center space-y-6">
          <div className="w-20 h-20 rounded-full bg-accent/10 flex items-center justify-center mx-auto">
            <Calendar className="w-10 h-10 text-accent" />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-center gap-2">
              <h2 className="text-2xl font-bold">Calendar</h2>
              <Badge variant="secondary" className="gap-1">
                <Construction className="w-3 h-3" />
                WIP
              </Badge>
            </div>
            <p className="text-muted-foreground">
              Course scheduling and calendar features are coming soon. Stay tuned!
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
