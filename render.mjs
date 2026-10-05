// Render Graphviz DOT from stdin to an SVG file, using the WebAssembly build of Graphviz
// Usage: makegraph --dot Makefile | node render.mjs output.svg

import { readFileSync, writeFileSync } from "node:fs";
import { Graphviz } from "./graphviz/graphviz.mjs";

const output = process.argv[2];
if (!output) {
    console.error("usage: node render.mjs output.svg < graph.dot");
    process.exit(1);
}

const graphviz = await Graphviz.load();
try {
    const svg = graphviz.dot(readFileSync(0, "utf8"));
    // remove the <title> Graphviz gives the graph, every node, and every edge, which browsers
    // show as tooltips (same as remove_titles() in makegraph)
    writeFileSync(output, svg.replace(/<title>[^<]*<\/title>\n?/g, ""));
} catch (e) {
    console.error(`render: ${e.message}`);
    process.exit(1);
}
