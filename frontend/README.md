# UW Guide – Frontend

This is the frontend for UW Guide – a web application for visualizing and exploring courses at the University of Waterloo. It is built with React, TypeScript.

## Introduction

UW Guide is designed to help students and users:

- Browse and search for University of Waterloo courses
- Visualize prerequisites, corequisites, and antirequisites
- Explore course dependency graphs
- Access detailed course information
- **(Coming soon)**: Receive personalized course recommendations based on inputs such as resumes, transcripts, and past work history

This project is part of a larger system that parses and manages course data from the University of Waterloo course catalog, with the future goal of providing intelligent, personalized guidance for academic planning.

## Setup Instructions

1. **Install dependencies**

   Make sure you have [Node.js](https://nodejs.org/) (v18 or newer recommended) and [npm](https://www.npmjs.com/) installed.

   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server**

   ```bash
   npm run dev
   ```

   This will start the app at [http://localhost:5173](http://localhost:5173) with hot module reloading.

3. **Build for production**

   ```bash
   npm run build
   ```

4. **Preview the production build**

   ```bash
   npm run preview
   ```

5. **Lint the code**

   ```bash
   npm run lint
   ```

---
