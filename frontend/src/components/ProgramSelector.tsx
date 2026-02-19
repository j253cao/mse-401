import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { ENGINEERING_PROGRAMS } from "@/constants/engineeringPrograms";
import { cn } from "@/lib/utils";

interface ProgramSelectorProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
}

export function ProgramSelector({
  value,
  onChange,
  disabled = false,
  className,
}: ProgramSelectorProps) {
  return (
    <div className={cn("space-y-2", className)}>
      <Label htmlFor="program-select">Engineering program</Label>
      <Select value={value || undefined} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger id="program-select" className="w-full">
          <SelectValue placeholder="Select your engineering program" />
        </SelectTrigger>
        <SelectContent>
          {ENGINEERING_PROGRAMS.map((program) => (
            <SelectItem key={program.code} value={program.code}>
              {program.displayName}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
