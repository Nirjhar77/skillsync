(function () {
    function byId(id) {
        return document.getElementById(id);
    }

    function safeList(value) {
        return Array.isArray(value) ? value : [];
    }

    function clearGraphSelection() {
        document.querySelectorAll(".graph-node.active-link").forEach((el) => el.classList.remove("active-link"));
    }

    function focusTimeline(anchorId, graphNode) {
        const target = document.getElementById(anchorId);
        if (!target) return;
        document.querySelectorAll(".overview-focus").forEach((el) => el.classList.remove("overview-focus"));
        clearGraphSelection();
        if (graphNode) {
            graphNode.classList.add("active-link");
        }
        target.scrollIntoView({ behavior: "smooth", block: "center" });
        const phase = target.closest(".phase-block");
        if (phase) phase.classList.add("overview-focus");
    }

    function renderSidebar(insight, fallback) {
        const titleEl = byId("topic-title");
        const subtitleEl = byId("topic-subtitle");
        const bodyEl = byId("topic-sidebar-body");
        if (!titleEl || !subtitleEl || !bodyEl) return;

        titleEl.textContent = insight.topic || fallback.title;
        subtitleEl.textContent = fallback.phaseTitle ? "Phase: " + fallback.phaseTitle : "Roadmap topic insight";

        function listHtml(items) {
            return safeList(items).map((x) => "<li>" + x + "</li>").join("");
        }

        bodyEl.innerHTML =
            '<div class="topic-section"><h4>Why It Matters</h4><p>' +
            (insight.why_it_matters || fallback.description || "No summary available.") +
            "</p></div>" +
            '<div class="topic-section"><h4>Prerequisites</h4><ul>' +
            listHtml(insight.prerequisites) +
            "</ul></div>" +
            '<div class="topic-section"><h4>Learning Path</h4><ul>' +
            listHtml(insight.learning_path) +
            "</ul></div>" +
            '<div class="topic-section"><h4>Practice Task</h4><p>' +
            (insight.practice_task || "Build a small practical exercise for this topic.") +
            "</p></div>" +
            '<div class="topic-section"><h4>Interview Checks</h4><ul>' +
            listHtml(insight.interview_checks) +
            "</ul></div>";
    }

    async function fetchTopicInsight(nodeData) {
        const bodyEl = byId("topic-sidebar-body");
        if (bodyEl) {
            bodyEl.innerHTML = '<div class="topic-loading">Generating AI topic insight...</div>';
        }
        try {
            const res = await fetch("/career/topic_insight", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    roadmap_id: window.ROADMAP_ID,
                    topic_title: nodeData.title,
                    topic_description: nodeData.description || "",
                    phase_title: nodeData.phaseTitle || "",
                }),
            });
            const payload = await res.json();
            if (!payload.success) {
                throw new Error(payload.error || "Failed to fetch topic insight");
            }
            renderSidebar(payload.insight || {}, nodeData);
        } catch (err) {
            renderSidebar(
                {
                    topic: nodeData.title,
                    why_it_matters: nodeData.description || "AI insight currently unavailable.",
                    prerequisites: [],
                    learning_path: [],
                    practice_task: "Review this topic and connect it to the next milestone.",
                    interview_checks: [],
                },
                nodeData
            );
        }
    }

    function applyTransform(targetA, targetB, state) {
        const t = "translate(" + state.x + "px, " + state.y + "px) scale(" + state.scale + ")";
        targetA.style.transform = t;
        targetB.style.transform = t;
    }

    document.addEventListener("DOMContentLoaded", function () {
        const mapEl = byId("overview-map");
        const viewportEl = byId("graph-viewport");
        const graphLayer = byId("graph-layer");
        const edgesSvg = byId("overview-edges");
        const rawData = byId("overview-graph-data");
        if (!mapEl || !viewportEl || !graphLayer || !edgesSvg || !rawData) return;

        const graph = JSON.parse(rawData.textContent || "{}");
        const phaseNodes = safeList(graph.phase_nodes);
        const milestoneNodes = safeList(graph.milestone_nodes);
        const edges = safeList(graph.edges);
        const allNodes = phaseNodes.concat(milestoneNodes);

        const colWidth = 210;
        const rowHeight = 82;
        const nodeWidth = 180;
        const nodeHeight = 58;
        const startX = 40;
        const startY = 30;

        const maxCol = Math.max(0, ...allNodes.map((n) => Number(n.x || 0)));
        const maxRow = Math.max(0, ...allNodes.map((n) => Number(n.y || 0)));
        const canvasWidth = startX + (maxCol + 1) * colWidth + 50;
        const canvasHeight = startY + (maxRow + 1) * rowHeight + 70;

        graphLayer.style.width = canvasWidth + "px";
        graphLayer.style.height = canvasHeight + "px";
        edgesSvg.setAttribute("width", String(canvasWidth));
        edgesSvg.setAttribute("height", String(canvasHeight));
        edgesSvg.setAttribute("viewBox", "0 0 " + canvasWidth + " " + canvasHeight);

        const nodeIndex = new Map();

        function putNode(node, isPhase) {
            const left = startX + Number(node.x || 0) * colWidth;
            const top = startY + Number(node.y || 0) * rowHeight;
            const el = document.createElement("button");
            el.type = "button";
            el.className = "graph-node " + (isPhase ? "phase-node" : "topic-node") + " status-" + (node.status || "not_started");
            el.style.left = left + "px";
            el.style.top = top + "px";
            el.style.width = nodeWidth + "px";
            el.style.height = nodeHeight + "px";
            el.innerHTML =
                '<span class="graph-node-kicker">' +
                (isPhase ? "Phase " + (node.phase_number || "") : "Topic " + (node.order || "")) +
                "</span>" +
                '<span class="graph-node-title">' +
                (node.title || "Untitled") +
                "</span>";

            nodeIndex.set(node.id, {
                x: left + nodeWidth / 2,
                y: top + nodeHeight / 2,
                node: node,
                el: el,
            });
            graphLayer.appendChild(el);

            el.addEventListener("click", function () {
                clearGraphSelection();
                el.classList.add("active-link");
                focusTimeline(node.anchor, el);
                fetchTopicInsight({
                    title: node.title,
                    description: node.description || "",
                    phaseTitle: node.phase_number ? "Phase " + node.phase_number : "",
                });
            });
        }

        phaseNodes.forEach((node) => putNode(node, true));
        milestoneNodes.forEach((node) => putNode(node, false));

        edgesSvg.innerHTML = edges
            .map((edge) => {
                const from = nodeIndex.get(edge.from);
                const to = nodeIndex.get(edge.to);
                if (!from || !to) return "";
                const cls = edge.type === "phase" ? "phase-link" : "milestone-link";
                return (
                    '<line class="' +
                    cls +
                    '" x1="' +
                    from.x +
                    '" y1="' +
                    from.y +
                    '" x2="' +
                    to.x +
                    '" y2="' +
                    to.y +
                    '"></line>'
                );
            })
            .join("");

        const transformState = { x: 0, y: 0, scale: 1 };
        applyTransform(graphLayer, edgesSvg, transformState);

        byId("graph-zoom-in")?.addEventListener("click", function () {
            transformState.scale = Math.min(2.2, transformState.scale + 0.15);
            applyTransform(graphLayer, edgesSvg, transformState);
        });
        byId("graph-zoom-out")?.addEventListener("click", function () {
            transformState.scale = Math.max(0.5, transformState.scale - 0.15);
            applyTransform(graphLayer, edgesSvg, transformState);
        });
        byId("graph-reset")?.addEventListener("click", function () {
            transformState.scale = 1;
            transformState.x = 0;
            transformState.y = 0;
            applyTransform(graphLayer, edgesSvg, transformState);
        });

        let dragging = false;
        let startClientX = 0;
        let startClientY = 0;
        let dragStartX = 0;
        let dragStartY = 0;
        viewportEl.addEventListener("pointerdown", function (e) {
            if (e.target.closest(".graph-node")) return;
            dragging = true;
            startClientX = e.clientX;
            startClientY = e.clientY;
            dragStartX = transformState.x;
            dragStartY = transformState.y;
            viewportEl.setPointerCapture(e.pointerId);
        });
        viewportEl.addEventListener("pointermove", function (e) {
            if (!dragging) return;
            transformState.x = dragStartX + (e.clientX - startClientX);
            transformState.y = dragStartY + (e.clientY - startClientY);
            applyTransform(graphLayer, edgesSvg, transformState);
        });
        viewportEl.addEventListener("pointerup", function () {
            dragging = false;
        });

        viewportEl.addEventListener(
            "wheel",
            function (e) {
                e.preventDefault();
                const delta = e.deltaY > 0 ? -0.08 : 0.08;
                transformState.scale = Math.max(0.5, Math.min(2.2, transformState.scale + delta));
                applyTransform(graphLayer, edgesSvg, transformState);
            },
            { passive: false }
        );
    });
})();
