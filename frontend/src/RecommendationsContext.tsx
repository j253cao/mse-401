import React, { createContext, useState } from "react";

export type Course = { code: string; title: string; description?: string };

export const RecommendationsContext = createContext<{
  recommendedCourses: Course[];
  setRecommendedCourses: React.Dispatch<React.SetStateAction<Course[]>>;
}>({
  recommendedCourses: [],
  setRecommendedCourses: () => {},
});

export const RecommendationsProvider: React.FC<{
  children: React.ReactNode;
}> = ({ children }) => {
  const [recommendedCourses, setRecommendedCourses] = useState<Course[]>([]);
  return (
    <RecommendationsContext.Provider
      value={{ recommendedCourses, setRecommendedCourses }}
    >
      {children}
    </RecommendationsContext.Provider>
  );
};
