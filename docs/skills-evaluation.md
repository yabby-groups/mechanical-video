# CAD Skill evaluation — 2026-10-27

Fetched both GitHub repositories' root listings and SKILL.md.

- baibai2013/build123d-cad: broad hardware orchestration with 25 subskills, robot simulation, electronics, manufacturing and viewer flows. Relevant mechanical coverage, but a much larger scope and router dependency than this rendering project needs. Evaluated, not installed.
- earthtojake/cad-skill: focused STEP-first build123d parts, assemblies, positive-volume validation, local placements and secondary STL export. Selected and installed with the official installer using an explicit project `--dest` into `.agents/skills/cad`. Its upstream license is included. No upstream scripts were executed during evaluation.

The project mechanical-video Skill takes precedence for rendering, uncertainty, resource limits and output paths. Upstream viewer/cloud/upload/manufacturing actions are outside this task. Installed Skills become discoverable on the next Codex turn.
