# GUI workspace icon and brand pass — phase 2

The existing Veilbreaker emblem is now visible in the sidebar and Overview as well as the app/window icon. A local SVG line-icon set identifies all seven workspaces in the sidebar, compact page selector and Navigate menu. Collector cards identify network, guided follow-up, cellular, Starlink, SDR and throughput inputs. Tool discovery cards carry category icons; primary run, evidence, map and SDR capture actions have matching icons.

The icons use local vector assets in `src/veilbreaker/assets/icons`; no web service, icon font or remote image is needed in the field. Package data and the frozen bundle include the new assets. Text labels and accessible names remain present, so icons do not become the sole meaning of a control.

The Overview action row wraps at field-window widths. The sidebar and 1280×720 Investigate view were visually checked, and narrow-page regression tests cover horizontal overflow. A later visual pass can add live hardware status badges and refine action density without claiming readiness before a device check.
