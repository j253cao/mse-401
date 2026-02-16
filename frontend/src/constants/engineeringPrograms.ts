/**
 * Engineering programs and required core courses mapping.
 * Programs are hardcoded (rarely change). Core courses extracted from degree_requirements.
 */

export const ENGINEERING_PROGRAMS = [
  { code: "AE", displayName: "Architectural Engineering" },
  { code: "BME", displayName: "Biomedical Engineering" },
  { code: "CHE", displayName: "Chemical Engineering" },
  { code: "CIVE", displayName: "Civil Engineering" },
  { code: "COMPE", displayName: "Computer Engineering" },
  { code: "ELE", displayName: "Electrical Engineering" },
  { code: "ENVE", displayName: "Environmental Engineering" },
  { code: "GEOE", displayName: "Geological Engineering" },
  { code: "ME", displayName: "Mechanical Engineering" },
  { code: "MGTE", displayName: "Management Engineering" },
  { code: "MTE", displayName: "Mechatronics Engineering" },
  { code: "NE", displayName: "Nanotechnology Engineering" },
  { code: "SE", displayName: "Software Engineering" },
  { code: "SYDE", displayName: "Systems Design Engineering" },
] as const;

export type EngineeringProgramCode = (typeof ENGINEERING_PROGRAMS)[number]["code"];

import type { IncomingLevel } from "@/types/api";
export type { IncomingLevel };

const TERM_ORDER: IncomingLevel[] = ["1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B"];

/** Required core courses per program per term. Generated from degree_requirements. */
import programCoreCourses from "@/data/program_core_courses.json";

type ProgramCoreCoursesMap = Record<string, Record<string, string[]>>;

/**
 * Get required core courses taken before the given incoming level.
 * E.g. incoming 2A -> returns courses from 1A and 1B.
 * Non-required electives come from transcript.
 */
export function getCoreCoursesBeforeLevel(
  programCode: string,
  incomingLevel: IncomingLevel
): string[] {
  const programCourses = (programCoreCourses as ProgramCoreCoursesMap)[programCode];
  if (!programCourses) return [];

  const incomingIndex = TERM_ORDER.indexOf(incomingLevel);
  if (incomingIndex <= 0) return [];

  const courses: string[] = [];
  for (let i = 0; i < incomingIndex; i++) {
    const term = TERM_ORDER[i];
    const termCourses = programCourses[term];
    if (termCourses) {
      courses.push(...termCourses);
    }
  }
  return [...new Set(courses)];
}
