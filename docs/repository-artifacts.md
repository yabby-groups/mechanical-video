# Maintained-source repository policy

Git tracks the maintained Python package, reusable tools, tests, configuration,
authored documentation and input contracts used by that code. File extension
alone is not a reason to commit a file.

The experiments/, reports/ and production-vault/ directories are local production
workspaces in their entirety. Their frozen scripts, per-run JSON, generated
reports, source downloads, CAD caches, scenes, media and logs do not belong in
Git. Permanent local retention and Git tracking are separate decisions.

Episode/session-specific helpers with fixed local paths are also local-only.
Reusable checks such as mechanical_video.cad_preflight and scene_preflight, and
their independent regression tests, remain maintained source.

Keep written analytics reviews and production briefs. Browser exports, screenshot
captures, cleanup manifests and usage dumps remain local. Program input data such
as docs/mechanical-terms.json and authored content contracts remain versioned.

Untracking does not authorize deleting assets, clearing protection flags,
regenerating media or repeating provider requests. Existing local submission
markers and production files must remain intact. Historical documents can refer
to local evidence without implying that its artifact is included in a clone.

Corrections rewrite only unpublished commits. Published history is preserved;
the active branch no longer tracks local production artifacts.
