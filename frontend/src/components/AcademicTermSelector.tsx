import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import type { IncomingLevel } from "@/types/api";
import { cn } from "@/lib/utils";

const ACADEMIC_LEVELS: IncomingLevel[] = ["1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B"];

interface AcademicTermSelectorProps {
  value: IncomingLevel | "";
  onChange: (value: IncomingLevel) => void;
  disabled?: boolean;
  className?: string;
}

export function AcademicTermSelector({
  value,
  onChange,
  disabled = false,
  className,
}: AcademicTermSelectorProps) {
  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor="term-select">Incoming academic term</Label>
      <Select
        value={value || undefined}
        onValueChange={(v) => onChange(v as IncomingLevel)}
        disabled={disabled}
      >
        <SelectTrigger id="term-select" className="w-full">
          <SelectValue placeholder="What term are you entering?" />
        </SelectTrigger>
        <SelectContent>
          {ACADEMIC_LEVELS.map((level) => (
            <SelectItem key={level} value={level}>
              {level}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
