/**
 * Utility to convert graph data (nodes and links) into a tree structure for Mind Map.
 * 
 * @param {Object} data - { nodes: [], links: [] }
 * @param {string} rootId - The ID of the root node (usually the search term).
 * @returns {Object} - Tree structure suitable for ECharts tree series.
 */
export const convertGraphToTree = (data, rootId) => {
    if (!data || !data.nodes || data.nodes.length === 0) return null;

    // 1. Index nodes by ID for quick access
    const nodeMap = {};
    data.nodes.forEach(node => {
        nodeMap[node.id] = { ...node };
    });

    // 2. Find the root node
    let root = nodeMap[rootId];
    if (!root) {
        // Fallback: Try to find a node with label matching rootId (case-insensitive)
        const potentialRoot = data.nodes.find(n => n.label.toLowerCase() === rootId?.toLowerCase());
        if (potentialRoot) {
            root = nodeMap[potentialRoot.id];
        } else {
             // Fallback: Pick the node with the most connections? Or just the first one?
             root = nodeMap[data.nodes[0].id];
        }
    }

    if (!root) return null;

    // 3. Build Adjacency List (Directed)
    const adj = {};
    data.links.forEach(link => {
        if (!adj[link.source]) adj[link.source] = [];
        adj[link.source].push({ target: link.target, relation: link.relation, desc: link.desc });
    });

    // 4. Recursive Build with Path-based Cycle Detection (Unrolling DAG)
    // This allows a node to appear multiple times if reached via different paths,
    // but prevents infinite loops.
    const buildTree = (currentNodeId, currentPath) => {
        const currentNode = nodeMap[currentNodeId];
        if (!currentNode) return null;

        // Cycle Detection: If this node is already in the current recursion path, stop.
        if (currentPath.has(currentNodeId)) {
            return {
                name: currentNode.label,
                value: currentNode.id, // Use ID as value
                // Mark as a reference/cycle end to maybe style differently?
                // For now, just stop expansion.
                ...currentNode,
                children: [] 
            };
        }

        const newPath = new Set(currentPath);
        newPath.add(currentNodeId);

        const neighbors = adj[currentNodeId] || [];
        const children = [];

        neighbors.forEach(edge => {
            const childNode = buildTree(edge.target, newPath);
            if (childNode) {
                // Add relation info to the child for tooltip/edge label
                childNode.relationToParent = edge.relation;
                childNode.relationDesc = edge.desc;
                children.push(childNode);
            }
        });

        return {
            name: currentNode.label,
            value: currentNode.id,
            ...currentNode,
            children: children.length > 0 ? children : undefined
        };
    };

    return buildTree(root.id, new Set());
};
