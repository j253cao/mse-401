import allOptions from "@/data/all_options.json";
import type { OptionDefinition, RequirementNode, GroupNode } from "@/types/api";

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

const options = allOptions as unknown as OptionDefinition[];

function normalize(code: string): string {
  return code.toUpperCase().replace(/\s+/g, "");
}

interface NodeResult {
  satisfied: boolean;
  completedCourses: string[];
}

function evaluateNode(node: RequirementNode, completedSet: Set<string>): NodeResult {
  if (node.type === "course") {
    const satisfied = completedSet.has(normalize(node.code));
    return { satisfied, completedCourses: satisfied ? [node.code] : [] };
  }

  const childResults = node.children.map((child) => evaluateNode(child, completedSet));
  const allCompleted = childResults.flatMap((r) => r.completedCourses);

  if (node.type === "AND") {
    const satisfied = childResults.every((r) => r.satisfied);
    return { satisfied, completedCourses: allCompleted };
  }

  // OR node
  const required = node.required_count ?? node.children.length;
  const satisfiedChildren = childResults.filter((r) => r.satisfied);
  const satisfied = satisfiedChildren.length >= required;
  return { satisfied, completedCourses: allCompleted };
}

function countLeafCourses(node: RequirementNode): number {
  if (node.type === "course") return 1;
  return node.children.reduce((sum, child) => sum + countLeafCourses(child), 0);
}

export function computeOptionsProgress(
  completedCourses: string[],
): OptionProgress[] {
  const completedSet = new Set(completedCourses.map(normalize));

  const results: OptionProgress[] = options
    .filter((opt) => opt.course_requirements?.children?.length > 0)
    .map((option) => {
      const root: GroupNode = option.course_requirements;

      // Map each top-level child of root AND → one ListProgress row
      const lists: ListProgress[] = root.children.map((child) => {
        const result = evaluateNode(child, completedSet);
        const required_count =
          child.type === "course"
            ? 1
            : child.type === "AND"
              ? child.children.length
              : (child.required_count ?? child.children.length);
        const total_courses = countLeafCourses(child);
        const list_name =
          child.type === "course" ? child.code : child.description;

        return {
          list_name,
          required_count,
          total_courses,
          completed_courses: result.completedCourses,
          is_satisfied: result.satisfied,
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
