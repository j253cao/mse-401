# UW Academic Calendar – Programs & Minors Data

This folder holds scraped data from the [University of Waterloo Undergraduate Academic Calendar](https://uwaterloo.ca/academic-calendar/undergraduate-studies/catalog#/programs?expanded=).

## Source

- **Index:** https://uwaterloo.ca/academic-calendar/undergraduate-studies/catalog#/programs?expanded=
- **Example program:** [Accounting and Financial Management (Honours)](https://uwaterloo.ca/academic-calendar/undergraduate-studies/catalog#/programs/rkZgeyACi3?expanded=&bc=true&bcCurrent=Accounting%20and%20Financial%20Management%20(Bachelor%20of%20Accounting%20and%20Financial%20Management%20-%20Honours)&bcGroup=Accounting%20and%20Financial%20Management&bcItemType=programs)

## How to scrape

From the repo root:

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
python -m scrapers.calendar_catalog_scraper
```

Options:

- `--output-dir PATH` – Write JSON files here (default: `data/programs`)
- `--no-headless` – Show the browser window
- `--delay SECONDS` – Pause between pages (default: 1.0)
- `--minors-only` – **Scrape all minors:** load catalog search `?searchTerm=minor`, collect links, scrape each → `all_programs.json`.
- `--options-only` – **Scrape Engineering Options:** load [Engineering Options](https://uwaterloo.ca/engineering/undergraduate-students/degree-enhancement/options), collect catalog links, scrape each → `all_options.json`.
- `--filter WORD ...` – Only scrape programs whose name or URL contains any of these words.
- `--limit N` – Scrape only the first N matching links (e.g. `--options-only --limit 3`).

## Output files

After a run you should see:

- **`programs_index.json`** or **`options_index.json`** – List of links found (minors search or Engineering Options page).
- **`all_programs.json`** (minors) or **`all_options.json`** (options) – Single array of scraped programs. Minors use `program_name`; options use `option_name`. Both include `course_lists`. No per-program files are written.

## Per-program JSON shape

Each program file includes:

| Field | Description |
|-------|-------------|
| `url` | Calendar URL for this program |
| `title` | Main heading (e.g. "Accounting and Financial Management (Bachelor of ... - Honours)") |
| `breadcrumb` | Breadcrumb text |
| `system_of_study` | e.g. `["Co-operative", "Regular"]` |
| `admission_requirements` | Sections like minimum requirements, minimum averages |
| `graduation_requirements` | Unit requirements, communication requirement, co-op requirements, notes |
| `study_work_sequence` | Table and legend for study/work terms |
| `course_requirements` | Required/elective text and course blocks |
| `raw_sections` | Fallback main content for parsing |

The page is a JavaScript SPA; the scraper uses Playwright so the catalog content is fully loaded before extraction.
