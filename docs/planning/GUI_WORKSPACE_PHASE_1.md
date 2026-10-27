# GUI workspace cleanup — phase 1

The desktop sidebar now follows the agreed field workflow: Overview, Investigate, Evidence, Surveys, Configuration, Tools, Settings. Page order, compact navigation, keyboard navigation, and packaged GUI screenshots follow that same order.

Investigate retains the current diagnostic engine and inputs. Optional collectors appear as explanatory cards, with their existing checkboxes and run plan intact. Evidence contains run history, reports, comparisons, cases, deletion/restore, ZIP verification, and interrupted-capture recovery. Configuration contains connection targets, hardware settings, regional packs, receiver presets and readiness. Settings contains data location and advanced JSON configuration. Normal connection setup no longer appears under Settings.

This is a navigation and workflow pass over the existing PySide6 application. Follow-on visual work should address status badges and hardware readiness cards, then reduce permanent action density in Evidence and Configuration. Any status indicator must reflect an actual check rather than assuming hardware is present. Continue checking narrow field windows and application scaling.
