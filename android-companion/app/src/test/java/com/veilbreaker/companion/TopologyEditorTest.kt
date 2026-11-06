package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class TopologyEditorTest {
    @Test fun addsNamedNodesAndRejectsInvalidOrDuplicateNames() {
        val empty = TopologyEditor.State()
        val one = TopologyEditor.addNode(empty, "  Router  ")!!
        assertEquals(listOf("Router"), one.nodes)
        assertTrue(empty.nodes.isEmpty())
        assertNull(TopologyEditor.addNode(one, "Router"))
        assertNull(TopologyEditor.addNode(one, ""))
        assertNull(TopologyEditor.addNode(one, "Bad\nNode"))
        assertNull(TopologyEditor.addNode(one, "A".repeat(25)))
    }

    @Test fun linksAreUndirectedAndCannotSelfConnectOrDuplicate() {
        val nodes = TopologyEditor.State(listOf("Router", "Switch", "AP"))
        val linked = TopologyEditor.addLink(nodes, 0, 1)!!
        assertNull(TopologyEditor.addLink(linked, 1, 0))
        assertNull(TopologyEditor.addLink(linked, 1, 1))
        assertNull(TopologyEditor.addLink(linked, 0, 5))
        assertEquals(listOf("Switch"), TopologyEditor.neighbors(linked, 0))
        assertTrue(TopologyEditor.removeLink(linked, 1, 0)!!.links.isEmpty())
    }

    @Test fun deletingNodeRemovesItsLinksAndRemapsTheOthers() {
        val original = TopologyEditor.State(listOf("Router", "Switch", "AP", "Server"), listOf(0 to 1, 1 to 2, 2 to 3))
        val updated = TopologyEditor.removeNode(original, 1)!!
        assertEquals(listOf("Router", "AP", "Server"), updated.nodes)
        assertEquals(listOf(1 to 2), updated.links)
        assertEquals(listOf(0 to 1, 1 to 2, 2 to 3), original.links)
        assertNull(TopologyEditor.removeNode(original, -1))
    }

    @Test fun respectsGraphLimits() {
        val full = TopologyEditor.State((1..12).map { "Node $it" })
        assertNull(TopologyEditor.addNode(full, "extra"))
        val links = (0..11).flatMap { a -> ((a + 1)..11).map { b -> a to b } }.take(30)
        assertEquals(30, links.size)
        assertNull(TopologyEditor.addLink(TopologyEditor.State(full.nodes, links), 10, 11))
    }
}
