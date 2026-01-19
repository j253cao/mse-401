import React, { createContext, useState } from "react";

export type Course = { code: string; title: string; description?: string };

export type TermSummary = {
  term_id: number;
  term_name: string;
  level: string;
  courses: string[];
};

export type StudentProfile = {
  program: string;
  studentNumber: number;
  latestTerm: TermSummary | null;
};

export const RecommendationsContext = createContext<{
  recommendedCourses: Course[];
  setRecommendedCourses: React.Dispatch<React.SetStateAction<Course[]>>;
  completedCourses: string[];
  setCompletedCourses: React.Dispatch<React.SetStateAction<string[]>>;
  studentProfile: StudentProfile | null;
  setStudentProfile: React.Dispatch<React.SetStateAction<StudentProfile | null>>;
  termSummaries: TermSummary[];
  setTermSummaries: React.Dispatch<React.SetStateAction<TermSummary[]>>;
}>({
  recommendedCourses: [],
  setRecommendedCourses: () => {},
  completedCourses: [],
  setCompletedCourses: () => {},
  studentProfile: null,
  setStudentProfile: () => {},
  termSummaries: [],
  setTermSummaries: () => {},
});

export const RecommendationsProvider: React.FC<{
  children: React.ReactNode;
}> = ({ children }) => {
  const [recommendedCourses, setRecommendedCourses] = useState<Course[]>([]);
  const [completedCourses, setCompletedCourses] = useState<string[]>([]);
  const [studentProfile, setStudentProfile] = useState<StudentProfile | null>(null);
  const [termSummaries, setTermSummaries] = useState<TermSummary[]>([]);
  
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
      }}
    >
      {children}
    </RecommendationsContext.Provider>
  );
};
