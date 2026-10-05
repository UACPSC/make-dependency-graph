# make-dependency-graph

Generates an SVG dependency graph from a Makefile.

The first non-blank comment line in the Makefile becomes the graph's title.

Hovering over a target shows its rule, with the comment and `.PHONY` line just before it. Tooltips only work when the SVG is opened directly, such as
with GitHub's **Raw** button, not in GitHub's file view or in a README image:

    https://raw.githubusercontent.com/<owner>/<repo>/diagrams/makegraph.svg

Edges point from a target to its prerequisites. Node colors:

- green: phony targets (`.PHONY`)
- red: generated files (targets with rules)
- black: source files (prerequisites only)

## Add to a repo

In the repo, choose **Actions → New workflow → Makefile dependency graph**, or copy
[`example/makegraph.yml`](example/makegraph.yml) to `.github/workflows/makegraph.yml`.

Every push to `main` that changes a `Makefile` regenerates `makegraph.svg` (one next to each Makefile)
and commits it to the `diagrams` branch, so `main` only has your own commits. View it at:

    https://github.com/<owner>/<repo>/blob/diagrams/makegraph.svg

To create the graph right away, run the workflow from the Actions tab.

To use a different branch:

```yaml
jobs:
  graph:
    uses: UACPSC/make-dependency-graph/.github/workflows/makegraph.yml@main
    with:
      branch: graphs
```

## How it renders

In the action, `makegraph --dot` produces the Graphviz source and `render.mjs` renders it with a
WebAssembly build of Graphviz (in `graphviz/`) on the runner's preinstalled Node, so nothing has to
be installed. Locally, `makegraph` uses the Graphviz `dot` command.

## Run locally

Requires Python 3 and [Graphviz](https://graphviz.org).

    ./makegraph                    # reads Makefile, writes makegraph.svg
    ./makegraph other.mk -o deps.svg
    ./makegraph --dot              # print the Graphviz source
