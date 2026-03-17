import React, { createContext, useState, useEffect, useCallback, useRef } from "react";
import type { Course, TermSummary, StudentProfile, IncomingLevel } from "@/types/api";
import { useStoredProfile } from "@/hooks/useStoredProfile";
import { getCoreCoursesBeforeLevel } from "@/constants/engineeringPrograms";
import { type DepartmentFilters, INITIAL_DEPARTMENTS } from "@/constants/filterDepartments";

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
  clearProfile: () => void;
  search: string;
  setSearch: React.Dispatch<React.SetStateAction<string>>;
  filteredCourses: Course[];
  setFilteredCourses: React.Dispatch<React.SetStateAction<Course[]>>;
  departments: DepartmentFilters;
  setDepartments: React.Dispatch<React.SetStateAction<DepartmentFilters>>;
  includeOtherDepts: boolean;
  setIncludeOtherDepts: React.Dispatch<React.SetStateAction<boolean>>;
  includeUndergrad: boolean;
  setIncludeUndergrad: React.Dispatch<React.SetStateAction<boolean>>;
  includeGrad: boolean;
  setIncludeGrad: React.Dispatch<React.SetStateAction<boolean>>;
  selectedOptions: string[];
  setSelectedOptions: React.Dispatch<React.SetStateAction<string[]>>;
  explorationMode: boolean;
  setExplorationMode: React.Dispatch<React.SetStateAction<boolean>>;
  hasSearched: boolean;
  setHasSearched: React.Dispatch<React.SetStateAction<boolean>>;
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
  clearProfile: () => {},
  search: "",
  setSearch: () => {},
  filteredCourses: [],
  setFilteredCourses: () => {},
  departments: INITIAL_DEPARTMENTS,
  setDepartments: () => {},
  includeOtherDepts: false,
  setIncludeOtherDepts: () => {},
  includeUndergrad: true,
  setIncludeUndergrad: () => {},
  includeGrad: true,
  setIncludeGrad: () => {},
  selectedOptions: [],
  setSelectedOptions: () => {},
  explorationMode: false,
  setExplorationMode: () => {},
  hasSearched: false,
  setHasSearched: () => {},
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
  const [search, setSearch] = useState("");
  const [filteredCourses, setFilteredCourses] = useState<Course[]>([]);
  const [departments, setDepartments] = useState<DepartmentFilters>(INITIAL_DEPARTMENTS);
  const [includeOtherDepts, setIncludeOtherDepts] = useState(false);
  const [includeUndergrad, setIncludeUndergrad] = useState(true);
  const [includeGrad, setIncludeGrad] = useState(true);
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [explorationMode, setExplorationMode] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const hasLoadedFromStorage = useRef(false);
  const skipNextAutoPopulate = useRef(false);

  // Load from localStorage on mount
  useEffect(() => {
    const stored = read();
    if (stored) {
      setProgramCode(stored.programCode);
      setIncomingLevel(stored.incomingLevel);
      setIncludeGrad(!stored.incomingLevel);
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

  const clearProfile = useCallback(() => {
    setProgramCode("");
    setIncomingLevel("");
    setCompletedCourses([]);
    setRecommendedCourses([]);
    setStudentProfile(null);
    setTermSummaries([]);
    setSearch("");
    setFilteredCourses([]);
    setDepartments(INITIAL_DEPARTMENTS);
    setIncludeOtherDepts(false);
    setIncludeUndergrad(true);
    setIncludeGrad(true);
    setSelectedOptions([]);
    setExplorationMode(false);
    setHasSearched(false);
    skipNextAutoPopulate.current = true;
    write(null);
  }, [write]);

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
        clearProfile,
        search,
        setSearch,
        filteredCourses,
        setFilteredCourses,
        departments,
        setDepartments,
        includeOtherDepts,
        setIncludeOtherDepts,
        includeUndergrad,
        setIncludeUndergrad,
        includeGrad,
        setIncludeGrad,
        selectedOptions,
        setSelectedOptions,
        explorationMode,
        setExplorationMode,
        hasSearched,
        setHasSearched,
      }}
    >
      {children}
    </RecommendationsContext.Provider>
  );
};
