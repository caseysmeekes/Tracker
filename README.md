# ATC Tender Tracker

A tender-monitoring application focused on opportunities in:

- Air Traffic Control simulators and simulation systems
- Air Traffic Control selection, aptitude and psychometric software
- Air Traffic Control training platforms, tools and training systems
- Procedure design, PBN, instrument flight procedure design and related software/services
- Aeronautical Information Management (AIM), AIS and related digital information systems

## Search approach

The application is designed to combine multiple keyword families rather than rely only on exact product names. It should score results for relevance and expose the original source URL, country, procuring organisation, deadline and matched category.

## Categories

### ATC Simulators
Keywords include: air traffic control simulator, ATC simulator, tower simulator, radar simulator, area control simulator, approach simulator, simulation training system, controller training simulator, fast-time simulation, real-time simulation.

### ATC Selection
Keywords include: air traffic controller selection, ATC selection, controller aptitude, ATCO aptitude, psychometric assessment, cognitive assessment, FEAST, controller recruitment testing, selection platform.

### ATC Training
Keywords include: air traffic control training, ATCO training, controller training, instructor training tools, training management system, e-learning for ATC, simulator-based training, competency assessment.

### Procedure Design
Keywords include: instrument flight procedure design, procedure design, PBN procedure design, IFP design, flight procedure design software, terminal procedure design, approach design, SID STAR design, obstacle assessment.

### AIM / AIS
Keywords include: aeronautical information management, AIM, aeronautical information services, AIS, AIXM, digital aeronautical information, aeronautical data management, eAIP, NOTAM management, aeronautical information system.

## Roadmap

1. Search multiple public tender sources and procurement portals.
2. Normalise results into a common record.
3. Deduplicate the same tender appearing across sources.
4. Score relevance by category and keyword strength.
5. Flag closing dates and newly published opportunities.
6. Provide direct source links.
7. Add scheduled daily monitoring through GitHub Actions.
