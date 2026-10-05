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
    writeFileSync(output, graphviz.dot(readFileSync(0, "utf8")));
} catch (e) {
    console.error(`render: ${e.message}`);
    process.exit(1);
}
