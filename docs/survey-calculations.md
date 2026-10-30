# Attach calculations to a survey

In **Tools**, calculate a result and use **Save result** with the **JSON
snapshot** option. Open a survey, select a point if appropriate, and choose
**Survey calculations**. Choose the point or **Survey-wide**, add optional
context, and attach the saved JSON. Select an attachment to review its inputs,
results, method and limitations. Remove an attachment from the active report
when it no longer applies; the survey journal retains its removal time.

Attachments are explicitly labeled **calculated estimates**, based on
operator-entered inputs. They are not measured signal or network evidence and
do not change the diagnostic, point metrics, or original evidence bundles.
Their details appear in the in-app survey report and in the exported
`survey_report.html` and `calculations.json`; the survey journal and export
integrity manifest retain the record as well.

The attachment workflow validates a supported version 1 calculator, finite
numeric inputs, current formula output, method and limitations. It also checks
the supported FSPL-to-link-budget handoff against its original inputs. A
snapshot whose results or metadata differ from the current calculator is not
silently recalculated: open the tool, review the inputs and assumptions, and
save a new snapshot. Reopen a completed survey before adding or removing an
attachment. File-based snapshots and input presets are different: presets save
inputs for reuse and are not accepted as finished calculations.
