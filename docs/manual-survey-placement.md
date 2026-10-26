# Manual survey placement

Open **Site surveys**, select a survey, and choose **Place points / floor plans…**.
Reopen completed surveys before editing. Select a collected scan or a planned point.
The unplaced count includes collected runs without qualified GPS or an operator placement;
planned points do not inflate that count.

For geographic placement, enter latitude/longitude or choose a point on the offline map,
then explicitly save. Purple pins identify operator positions. Captured GPS remains
separate and unchanged; an operator pin never becomes GPS evidence for terrain or tower analysis.

For indoor placement, import a labeled PNG/JPEG floor plan, select the floor, click a
position, and save. Drag to pan, scroll to zoom, and use **Fit floor** to reset the view.
Use **Calibrate floor scale**, click two known points, and enter their real separation
in meters. Each floor retains its own image coordinates and scale.

Images are copied into survey storage and verified on read. The current importer accepts
images up to 2048 pixels per dimension and 20 MB, with up to 20 floors per survey.
The original image file is no longer needed after import. Survey exports include spatial
metadata and registered floor images. Trash/restore retains these assets with the survey.
Clear or move placements before removing a floor. An edit history preserves prior positions.

This phase provides placement and scale calibration. Metric coloring, floor annotations,
report rendering of floor plans, and estimated heat-map surfaces remain future work.
