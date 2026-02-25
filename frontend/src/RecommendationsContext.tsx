import React, { createContext, useState, useEffect, useCallback, useRef } from "react";
import type { Course, TermSummary, StudentProfile, IncomingLevel } from "@/types/api";
import { useStoredProfile } from "@/hooks/useStoredProfile";
import { getCoreCoursesBeforeLevel } from "@/constants/engineeringPrograms";

export type { Course, TermSummary, StudentProfile };

export const RecommendationsContext = createContext<{
  recommendedCourses: Course[];
  setRecommendedCourses: React.Dispatch<React.SetStateAction<Course[]>>;
  completedCourses: string[];
  setCompletedCourses: React.Dispatch<React.SetStateAction<string[]>>;
  studentProfile: StudentProfile | null;
  setStudentProfile: React.Dispatch<React.SetStateAction<StudentProfile | null>>;
  termSummaries: TermSummary[];
  setTermSummaries: React.Dispatch<React.SetStateAction<TermSummary[]>>;
  programCode: string;
  setProgramCode: React.Dispatch<React.SetStateAction<string>>;
  incomingLevel: IncomingLevel | "";
  setIncomingLevel: React.Dispatch<React.SetStateAction<IncomingLevel | "">>;
}>({
  recommendedCourses: [],
  setRecommendedCourses: () => {},
  completedCourses: [],
  setCompletedCourses: () => {},
  studentProfile: null,
  setStudentProfile: () => {},
  termSummaries: [],
  setTermSummaries: () => {},
  programCode: "",
  setProgramCode: () => {},
  incomingLevel: "",
  setIncomingLevel: () => {},
});

export const RecommendationsProvider: React.FC<{
  children: React.ReactNode;
}> = ({ children }) => {
  const { read, write } = useStoredProfile();
  const [recommendedCourses, setRecommendedCourses] = useState<Course[]>([]);
  const [completedCourses, setCompletedCourses] = useState<string[]>([]);
  const [studentProfile, setStudentProfile] = useState<StudentProfile | null>(null);
  const [termSummaries, setTermSummaries] = useState<TermSummary[]>([]);
  const [programCode, setProgramCode] = useState("");
  const [incomingLevel, setIncomingLevel] = useState<IncomingLevel | "">("");
  const hasLoadedFromStorage = useRef(false);
  const skipNextAutoPopulate = useRef(false);

  // Load from localStorage on mount
  useEffect(() => {
    const stored = read();
    if (stored) {
      setProgramCode(stored.programCode);
      setIncomingLevel(stored.incomingLevel);
      if (stored.completedCourses && stored.completedCourses.length > 0) {
        setCompletedCourses(stored.completedCourses);
        skipNextAutoPopulate.current = true;
      }
    }
    hasLoadedFromStorage.current = true;
  }, [read]);

  // Persist to localStorage when program, term, or completedCourses changes
  const persistProfile = useCallback(() => {
    if (programCode && incomingLevel) {
      write({ programCode, incomingLevel, completedCourses });
    } else {
      write(null);
    }
  }, [programCode, incomingLevel, completedCourses, write]);

  useEffect(() => {
    persistProfile();
  }, [persistProfile]);

  // Auto-populate completedCourses with core courses when program+term selected (no transcript)
  // Skip on initial load when we restored completedCourses from storage
  useEffect(() => {
    if (!hasLoadedFromStorage.current) return;
    if (skipNextAutoPopulate.current) {
      skipNextAutoPopulate.current = false;
      return;
    }
    if (programCode && incomingLevel && termSummaries.length === 0) {
      const coreCourses = getCoreCoursesBeforeLevel(programCode, incomingLevel);
      setCompletedCourses(coreCourses);
    }
  }, [programCode, incomingLevel, termSummaries.length]);

  return (
    <RecommendationsContext.Provider
      value={{
        recommendedCourses,
        setRecommendedCourses,
        completedCourses,
        setCompletedCourses,
        studentProfile,
        setStudentProfile,
        termSummaries,
        setTermSummaries,
        programCode,
        setProgramCode,
        incomingLevel,
        setIncomingLevel,
      }}
    >
      {children}
    </RecommendationsContext.Provider>
  );
};
