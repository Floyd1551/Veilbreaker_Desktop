package com.veilbreaker.companion

/** Operator sketches. Node order determines indexes in undirected links. */
object TopologyEditor {
    data class State(val nodes: List<String> = emptyList(), val links: List<Pair<Int, Int>> = emptyList())
    private const val MAX_NODES = 12
    private const val MAX_LINKS = 30

    fun addNode(state: State, raw: String): State? {
        val name = raw.trim()
        if (state.nodes.size >= MAX_NODES || name.isEmpty() || name.length > 24 ||
            name.any(Char::isISOControl) || name.contains('>') || name in state.nodes) return null
        return state.copy(nodes = state.nodes + name)
    }

    fun removeNode(state: State, index: Int): State? {
        if (index !in state.nodes.indices) return null
        val remaining = state.nodes.filterIndexed { i, _ -> i != index }
        val links = state.links.filter { (a, b) -> a != index && b != index }
            .map { (a, b) -> (if (a > index) a - 1 else a) to (if (b > index) b - 1 else b) }
        return State(remaining, links)
    }

    fun addLink(state: State, a: Int, b: Int): State? {
        if (a !in state.nodes.indices || b !in state.nodes.indices || a == b || state.links.size >= MAX_LINKS ||
            state.links.any { (x, y) -> (x == a && y == b) || (x == b && y == a) }) return null
        return state.copy(links = state.links + (a to b))
    }

    fun removeLink(state: State, a: Int, b: Int): State? {
        val index = state.links.indexOfFirst { (x, y) -> (x == a && y == b) || (x == b && y == a) }
        if (index < 0) return null
        return state.copy(links = state.links.filterIndexed { i, _ -> i != index })
    }

    fun neighbors(state: State, index: Int): List<String> {
        if (index !in state.nodes.indices) return emptyList()
        return state.links.mapNotNull { (a, b) -> when (index) { a -> state.nodes.getOrNull(b); b -> state.nodes.getOrNull(a); else -> null } }
    }
}
