package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class ToolVisualModelTest {
    @Test fun diagramsStateTheirAssumptionsAndUnknownToolsHaveNoDiagram() {
        assertEquals(ToolVisualModel.Kind.FRESNEL, ToolVisualModel.forTool("fresnel")!!.kind)
        assertTrue(ToolVisualModel.forTool("fresnel")!!.description.contains("not a terrain profile"))
        assertEquals(ToolVisualModel.Kind.EARTH, ToolVisualModel.forTool("bulge")!!.kind)
        assertEquals(ToolVisualModel.Kind.OPTICAL, ToolVisualModel.forTool("fiberloss")!!.kind)
        assertEquals(ToolVisualModel.Kind.WIFI_RASTER, ToolVisualModel.forTool("wifi6")!!.kind)
        assertTrue(ToolVisualModel.forTool("wifi6")!!.description.contains("not show channel width"))
        assertNull(ToolVisualModel.forTool("unknown"))
    }

    @Test fun markerUsesDistanceFromFirstEndpointAndHandlesExtremeInputs() {
        assertEquals(0.25f, ToolVisualModel.pathFraction(1.0, 3.0)!!, 0.0001f)
        assertEquals(0.5f, ToolVisualModel.pathFraction(Double.MAX_VALUE, Double.MAX_VALUE)!!, 0.0001f)
        assertNull(ToolVisualModel.pathFraction(0.0, 1.0))
        assertNull(ToolVisualModel.pathFraction(Double.NaN, 1.0))
        assertNull(ToolVisualModel.pathFraction(1.0, Double.POSITIVE_INFINITY))
    }
}
