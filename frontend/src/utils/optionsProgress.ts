import allOptions from "@/data/all_options.json";
import type { OptionDefinition } from "@/types/api";

export interface ListProgress {
  list_name: string;
  list_description?: string;
  required_count: number;
  total_courses: number;
  completed_courses: string[];
  is_satisfied: boolean;
}

export interface OptionProgress {
  option_name: string;
  lists: ListProgress[];
  satisfied_count: number;
  total_lists: number;
  completion_ratio: number;
}

const options = allOptions as OptionDefinition[];

function normalize(code: string): string {
  return code.toUpperCase().replace(/\s+/g, "");
}

export function computeOptionsProgress(
  completedCourses: string[],
): OptionProgress[] {
  const completedSet = new Set(completedCourses.map(normalize));

  const results: OptionProgress[] = options
    .filter((opt) => opt.course_lists.some((l) => l.courses.length > 0))
    .map((option) => {
      const lists: ListProgress[] = option.course_lists
        .filter((list) => list.courses.length > 0)
        .map((list) => {
          const completed = list.courses.filter((c) =>
            completedSet.has(normalize(c)),
          );
          return {
            list_name: list.list_name,
            list_description: list.list_description,
            required_count: list.required_count,
            total_courses: list.courses.length,
            completed_courses: completed,
            is_satisfied: completed.length >= list.required_count,
          };
        });

      const satisfied_count = lists.filter((l) => l.is_satisfied).length;
      const total_lists = lists.length;

      return {
        option_name: option.option_name,
        lists,
        satisfied_count,
        total_lists,
        completion_ratio: total_lists > 0 ? satisfied_count / total_lists : 0,
      };
    });

  results.sort((a, b) => b.completion_ratio - a.completion_ratio);
  return results;
}
