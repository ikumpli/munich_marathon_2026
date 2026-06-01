# PROJECT CONTEXT: Marathon Tracker & Training Plan
**Project Goal:** Develop a Python data pipeline to analyze, visualize, and track the training for my first marathon, publishing the results on GitHub Pages.

## 1. Athlete Profile & Athletic Goal
* **Name:** Iker
* **Physical:** 25 years old, 182 cm, 74 kg. Athletic background, good cardiovascular base, but a marathon debutant.
* **Marathon Date:** Sunday, October 11, 2026.
* **Plan Start Date:** Monday, June 1, 2026 (19 weeks of preparation).
* **Time Goal:** Sub 4 hours (Target average pace: ~5:40 min/km).
* **Availability:** 5 running days per week + 1 optional cross-training day (swimming preferred, padel/volleyball with caution).

## 2. Data Source & Structure
* **Current Source:** CSV file exported from Intervals.icu (original data from Garmin Forerunner 745).
* **Input Format:** `i600311_activities.csv`
* **Main Columns Relevant for Analysis:**
    * `id`: Unique identifier.
    * `Tipo`: Activity type (filter by 'Run' for main analysis, keep 'Swim' for global load).
    * `Fecha`: Date and time of the activity (ISO 8601 format).
    * `Distancia`: In meters (NEEDS TRANSFORMATION to kilometers).
    * `Tiempo en movimiento`: In seconds (NEEDS TRANSFORMATION to minutes).
    * `FC media`: Average heart rate (bpm).

## 3. Current Tech Stack (Phase 1 - MVP)
* **Language:** Python 3.x
* **Data Manipulation:** `pandas`
* **Visualization:** `plotly` (for interactive HTML charts) or `matplotlib`/`seaborn` (for static images).
* **Deployment:** Generation of static files (HTML/PNG) to be hosted on GitHub Pages.

## 4. Instructions for the AI Agent
Act as a Senior Data Scientist and an Expert Marathon Coach. When helping me write code, you must follow these guidelines:
1.  **Data Cleaning:** Always ensure dates are properly parsed using `pd.to_datetime()` and create calculated columns like pace (`min/km`) in both decimal format and string format (MM:SS).
2.  **Aggregation:** We will need functions to group data by week (accumulated weekly volume is crucial to avoid injuries).
3.  **Clean & Modular Code:** Create separate functions for (a) loading data, (b) cleaning/transforming data, and (c) generating visualizations.
4.  **Pace Calculation:** Running pace does not behave like a standard decimal variable (e.g., 5.5 min/km is actually 5:30 min/km). Keep this in mind when formatting chart axes.

## 5. Immediate Task
Develop a Python script that reads the CSV file, filters the running activities ('Run'), calculates the total weekly distance, and generates a bar chart showing the kilometer volume per week, along with a trend line of the average weekly pace.