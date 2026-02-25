/**
 * Engineering department filter options.
 * Matches the 14 UW Engineering departments used in course_dependency_parser.
 * Backend filters by startswith(prefix).
 */

export const FILTER_DEPARTMENTS = [
  { code: "AE", fullName: "Architectural Engineering", abbr: "AE" },
  { code: "BME", fullName: "Biomedical Engineering", abbr: "BME" },
  { code: "CHE", fullName: "Chemical Engineering", abbr: "CHE" },
  { code: "CIVE", fullName: "Civil Engineering", abbr: "CIVE" },
  { code: "ECE", fullName: "Electrical and Computer Engineering", abbr: "ECE" },
  { code: "ENVE", fullName: "Environmental Engineering", abbr: "ENVE" },
  { code: "GENE", fullName: "General Engineering", abbr: "GENE" },
  { code: "GEOE", fullName: "Geological Engineering", abbr: "GEOE" },
  { code: "ME", fullName: "Mechanical Engineering", abbr: "ME" },
  { code: "MTE", fullName: "Mechatronics Engineering", abbr: "MTE" },
  { code: "MSE", fullName: "Management Science and Engineering", abbr: "MSE" },
  { code: "NE", fullName: "Nanotechnology Engineering", abbr: "NE" },
  { code: "SE", fullName: "Software Engineering", abbr: "SE" },
  { code: "SYDE", fullName: "Systems Design Engineering", abbr: "SYDE" },
] as const;

export type FilterDepartmentCode = (typeof FILTER_DEPARTMENTS)[number]["code"];
