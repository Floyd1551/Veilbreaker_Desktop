# Survey operator observations

Open a survey, select a point if appropriate, then choose **Operator observations**.
Record a type, material, description and optional operator name. Choose
**Survey-wide** when the observation is not associated with one diagnostic.
The survey retains the time and stable observation ID. Unknown material is a
valid choice; describe only what the operator actually observed.

Select an observation and choose **Edit selected** to correct its point, type,
material, description or operator. Save changes or cancel the edit. The original
recorded time and ID remain intact, and the journal retains prior values and
an update time. Select **View edit history** to review previous and updated
values, including after survey completion. If another window changes the record, reload and review the
new values before editing or removing it.

Observations are operator-entered context, not measured material loss or proof of
reflection, diffraction, obstruction or a root cause. The point association
does not create GPS evidence or a precise obstacle position. The survey report
includes active observations and the export includes the survey journal and
its integrity manifest. The observations CSV prefixes formula-like cells with
an apostrophe for spreadsheet safety; `survey.json` retains the exact values.
Removed observations are hidden from the active report
but their removal time remains in the journal. Reopen a completed survey before
changing observations.

Select an observation and choose **Attach photo** to copy a JPEG or PNG into
survey-owned storage. The report displays an operator-photo preview and the
evidence ZIP includes the original bytes and integrity manifest. Originals may
contain EXIF location or other personal metadata, which is preserved in the
export; Veilbreaker does not turn that metadata into GPS evidence. Replace or
remove an attachment from the observation when it is no longer needed.
Photos are limited to 20 per survey and 20 MiB each. Reopen a completed survey
to change them. A missing or altered photo prevents export until resolved.

Dimensions, a separate map marker and a propagation model are not created.
Existing diagnostic evidence is not rewritten.
