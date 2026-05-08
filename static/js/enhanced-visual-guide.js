/**
 * SkillSync Enhanced Interactive Visual Guide
 * Professional features: Zoom, Pan, Search, Mini-map, Export, Keyboard shortcuts
 */

(function () {
    // Configuration
    const CONFIG = {
        node: {
            width: 180,
            height: 58,
            phaseHeight: 70,
            padding: 12
        },
        layout: {
            colWidth: 220,
            rowHeight: 78,
            startX: 60,
            startY: 50,
            spineWidth: 5
        },
        zoom: {
            min: 0.4,
            max: 2.5,
            step: 0.15,
            initial: 0.9
        },
        colors: {
            phase1: '#6366f1', // Indigo
            phase2: '#06b6d4', // Cyan
            phase3: '#10b981', // Emerald
            phase4: '#f59e0b', // Amber
            phase5: '#ec4899', // Pink
            completed: '#34d399',
            inProgress: '#22d3ee',
            active: '#a78bfa'
        }
    };

    // State
    let graphData = null;
    let transform = { x: 0, y: 0, scale: CONFIG.zoom.initial };
    let isDragging = false;
    let dragStart = { x: 0, y: 0 };
    let dragTransformStart = { x: 0, y: 0 };
    let selectedNode = null;
    let searchQuery = '';
    let isFullscreen = false;
    let completedTopics = new Set();
    let nodeMap = new Map();

    // DOM Elements
    const viewport = document.getElementById('graph-viewport');
    const canvas = document.getElementById('graph-canvas');
    const edgesLayer = document.getElementById('edges-layer');
    const nodesLayer = document.getElementById('nodes-layer');
    const minimap = document.getElementById('minimap');
    const minimapViewport = document.getElementById('minimap-viewport');
    const searchInput = document.getElementById('graph-search');
    const searchResults = document.getElementById('search-results');
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const resetBtn = document.getElementById('zoom-reset');
    const exportBtn = document.getElementById('export-btn');
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const legendContainer = document.getElementById('legend');

    // Initialize
    function init() {
        const dataEl = document.getElementById('graph-data');
        if (!dataEl) return;

        try {
            graphData = JSON.parse(dataEl.textContent);
            if (!graphData.sections || !Array.isArray(graphData.sections)) {
                console.error('Invalid graph data structure');
                return;
            }

            // Load saved state
            loadSavedState();

            // Build graph
            buildGraph();
            updateProgress();
            buildLegend();
            setupEventListeners();
            applyTransform();
            loadCompletedTopics();

            // Animate entrance
            setTimeout(() => animateEntrance(), 100);

        } catch (e) {
            console.error('Failed to initialize graph:', e);
        }
    }

    // Build graph layout
    function buildGraph() {
        // Clear existing
        nodesLayer.innerHTML = '';
        edgesLayer.innerHTML = '';
        nodeMap.clear();

        const sections = graphData.sections;
        const phases = {};
        let maxWidth = CONFIG.layout.startX;
        let maxHeight = CONFIG.layout.startY;

        // First pass: collect topics per phase and calculate positions
        sections.forEach((section, sectionIdx) => {
            const phase = section.phase || sectionIdx + 1;
            const topics = section.topics || [];
            const colCount = Math.ceil(topics.length / 2);

            phases[phase] = phases[phase] || {
                label: section.label,
                topics: [],
                x: CONFIG.layout.startX + (phase - 1) * CONFIG.layout.colWidth,
                y: CONFIG.layout.startY
            };

            // Position topics in two columns
            topics.forEach((topic, idx) => {
                const col = idx % 2; // 0 = left, 1 = right
                const row = Math.floor(idx / 2);
                const x = phases[phase].x + (col === 0 ? -CONFIG.layout.colWidth/2 : CONFIG.layout.colWidth/2);
                const y = phases[phase].y + 40 + row * CONFIG.layout.rowHeight;

                phases[phase].topics.push({
                    id: topic.id,
                    label: topic.label,
                    type: topic.type || 'required',
                    importance: topic.importance || 'important',
                    x,
                    y,
                    phase,
                    section: section.label,
                    description: topic.description || '',
                    resources: topic.resources || []
                });

                maxHeight = Math.max(maxHeight, y + CONFIG.node.height);
            });

            maxWidth = Math.max(maxWidth, phases[phase].x + CONFIG.layout.colWidth/2 + CONFIG.node.width/2);
        });

        // Set canvas size
        canvas.width = maxWidth + 100;
        canvas.height = maxHeight + 100;
        edgesLayer.setAttribute('width', canvas.width);
        edgesLayer.setAttribute('height', canvas.height);
        edgesLayer.setAttribute('viewBox', `0 0 ${canvas.width} ${canvas.height}`);

        // Draw edges first (so they're behind nodes)
        drawEdges(phases);

        // Create phase nodes and topic nodes
        Object.values(phases).forEach((phase, idx) => {
            // Phase node
            const phaseNode = createPhaseNode(phase, idx + 1);
            nodesLayer.appendChild(phaseNode);

            // Topic nodes
            phase.topics.forEach(topic => {
                const node = createTopicNode(topic);
                nodesLayer.appendChild(node);
                nodeMap.set(topic.id, node);
            });
        });

        // Update minimap
        updateMinimap();
    }

    // Create phase header node
    function createPhaseNode(phase, phaseNum) {
        const node = document.createElement('div');
        node.className = 'phase-node';
        node.dataset.phase = phaseNum;
        node.dataset.type = 'phase';
        node.style.left = (phase.x - CONFIG.node.width/2) + 'px';
        node.style.top = (phase.y - CONFIG.layout.rowHeight/2) + 'px';
        node.style.width = CONFIG.node.width + 'px';
        node.style.height = CONFIG.layout.rowHeight + 'px';

        const color = CONFIG.colors[`phase${phaseNum}`] || CONFIG.colors.phase1;

        node.innerHTML = `
            <div class="phase-kicker">PHASE ${phaseNum}</div>
            <div class="phase-title" style="color: ${color}">${phase.label}</div>
        `;

        node.addEventListener('click', () => focusPhase(phaseNum));
        return node;
    }

    // Create topic node
    function createTopicNode(topic) {
        const node = document.createElement('button');
        node.className = 'topic-node';
        node.dataset.id = topic.id;
        node.dataset.phase = topic.phase;
        node.dataset.type = topic.type;
        node.dataset.importance = topic.importance;
        node.style.left = (topic.x - CONFIG.node.width/2) + 'px';
        node.style.top = (topic.y - CONFIG.node.height/2) + 'px';
        node.style.width = CONFIG.node.width + 'px';
        node.style.height = CONFIG.node.height + 'px';

        const color = CONFIG.colors[`phase${topic.phase}`] || CONFIG.colors.phase1;
        const isCompleted = completedTopics.has(topic.id);
        if (isCompleted) node.classList.add('completed');

        node.innerHTML = `
            <span class="topic-type">${topic.type === 'optional' ? '<span class="opt-badge">opt</span>' : ''}</span>
            <span class="topic-label">${topic.label}</span>
        `;

        node.addEventListener('click', (e) => {
            e.stopPropagation();
            selectNode(topic, node);
        });

        node.addEventListener('mouseenter', (e) => showTooltip(topic, e));
        node.addEventListener('mouseleave', hideTooltip);

        return node;
    }

    // Draw connecting edges
    function drawEdges(phases) {
        let svgContent = '';

        Object.values(phases).forEach((phase, idx) => {
            const phaseNum = idx + 1;
            const color = CONFIG.colors[`phase${phaseNum}`];
            const phaseX = phase.x;

            // Vertical spine from phase to first topic
            if (phase.topics.length > 0) {
                const firstTopicY = phase.topics[0].y - CONFIG.node.height/2;

                // Phase to spine
                svgContent += `<line class="spine-vertical" x1="${phaseX}" y1="${phase.y + 30}" x2="${phaseX}" y2="${firstTopicY}" stroke="${color}" stroke-width="3" opacity="0.5"/>`;

                // Horizontal connectors to each topic
                phase.topics.forEach(topic => {
                    const topicCenterX = topic.x;
                    const topicCenterY = topic.y;

                    // Left side topics
                    if (topic.x < phaseX) {
                        svgContent += `<line class="connector-h" x1="${phaseX - 15}" y1="${topicCenterY}" x2="${topicCenterX + CONFIG.node.width/2}" y2="${topicCenterY}" stroke="${color}" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.4"/>`;
                    }
                    // Right side topics
                    else {
                        svgContent += `<line class="connector-h" x1="${phaseX + 15}" y1="${topicCenterY}" x2="${topicCenterX - CONFIG.node.width/2}" y2="${topicCenterY}" stroke="${color}" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.4"/>`;
                    }
                });
            }
        });

        edgesLayer.innerHTML = svgContent;
    }

    // Node selection
    function selectNode(topic, nodeEl) {
        // Deselect previous
        document.querySelectorAll('.topic-node.selected').forEach(n => n.classList.remove('selected'));

        nodeEl.classList.add('selected');
        selectedNode = topic;

        // Show detail panel
        showTopicDetail(topic);
    }

    // Show topic details in side panel
    function showTopicDetail(topic) {
        const panel = document.getElementById('topic-detail-panel');
        const titleEl = document.getElementById('topic-title');
        const metaEl = document.getElementById('topic-meta');
        const bodyEl = document.getElementById('topic-detail-body');

        if (!panel || !titleEl || !metaEl || !bodyEl) return;

        titleEl.textContent = topic.label;
        const color = CONFIG.colors[`phase${topic.phase}`] || CONFIG.colors.phase1;

        metaEl.innerHTML = `
            <span class="meta-badge" style="background: rgba(${hexToRgb(color)},0.15); color: ${color}; border: 1px solid rgba(${hexToRgb(color)},0.3)">
                Phase ${topic.phase}: ${topic.section}
            </span>
            <span class="meta-badge ${topic.type}">${topic.type}</span>
            <span class="meta-badge importance-${topic.importance}">${topic.importance}</span>
        `;

        bodyEl.innerHTML = `
            <div class="detail-section">
                <h4>Overview</h4>
                <p>${topic.description || 'No description available.'}</p>
            </div>
            ${topic.resources && topic.resources.length ? `
                <div class="detail-section">
                    <h4>Recommended Resources</h4>
                    <div class="resource-list">
                        ${topic.resources.map(r => `
                            <a href="${r.url || '#'}" target="_blank" class="resource-item">
                                <span class="resource-icon">${getResourceIcon(r.type)}</span>
                                <span class="resource-info">
                                    <span class="resource-title">${r.title}</span>
                                    <span class="resource-type">${r.type || 'resource'}</span>
                                </span>
                                <span class="resource-external">↗</span>
                            </a>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            <div class="detail-actions">
                <button class="action-btn ${completedTopics.has(topic.id) ? 'completed' : ''}"
                        onclick="toggleTopicCompletion('${topic.id}')">
                    ${completedTopics.has(topic.id) ? '✓ Completed' : 'Mark as Complete'}
                </button>
            </div>
        `;

        panel.classList.add('active');
    }

    // Tooltip
    function showTooltip(topic, e) {
        const existing = document.querySelector('.topic-tooltip');
        if (existing) existing.remove();

        const tooltip = document.createElement('div');
        tooltip.className = 'topic-tooltip';
        tooltip.innerHTML = `
            <div class="tooltip-title">${topic.label}</div>
            <div class="tooltip-meta">Phase ${topic.phase} • ${topic.type}</div>
        `;
        document.body.appendChild(tooltip);

        const rect = e.target.getBoundingClientRect();
        tooltip.style.left = rect.left + 'px';
        tooltip.style.top = (rect.bottom + 8) + 'px';
    }

    function hideTooltip() {
        const tooltip = document.querySelector('.topic-tooltip');
        if (tooltip) tooltip.remove();
    }

    // Progress tracking
    function toggleTopicCompletion(topicId) {
        if (completedTopics.has(topicId)) {
            completedTopics.delete(topicId);
        } else {
            completedTopics.add(topicId);
        }

        // Update UI
        const node = nodeMap.get(topicId);
        if (node) node.classList.toggle('completed', completedTopics.has(topicId));

        // Save and update progress
        saveCompletedTopics();
        updateProgress();

        // Update button if exists
        const btn = document.querySelector('.action-btn');
        if (btn) {
            btn.textContent = completedTopics.has(topicId) ? '✓ Completed' : 'Mark as Complete';
            btn.classList.toggle('completed', completedTopics.has(topicId));
        }
    }

    function updateProgress() {
        const total = Object.keys(nodeMap).length;
        const completed = completedTopics.size;
        const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

        if (progressBar) {
            progressBar.style.width = percent + '%';
            progressBar.setAttribute('aria-valuenow', percent);
        }
        if (progressText) progressText.textContent = `${completed}/${total} (${percent}%)`;
    }

    // Search functionality
    function performSearch(query) {
        query = query.toLowerCase().trim();
        searchQuery = query;

        document.querySelectorAll('.topic-node').forEach(node => {
            const label = node.querySelector('.topic-label')?.textContent.toLowerCase() || '';
            const matches = !query || label.includes(query);
            node.style.opacity = matches ? '1' : '0.3';
            node.style.pointerEvents = matches ? 'auto' : 'none';
        });

        if (query) {
            searchResults.classList.add('active');
            const matches = Array.from(nodeMap.values()).filter(node =>
                node.querySelector('.topic-label')?.textContent.toLowerCase().includes(query)
            );
            searchResults.textContent = `${matches.length} match${matches.length !== 1 ? 'es' : ''}`;
        } else {
            searchResults.classList.remove('active');
        }
    }

    // Zoom & Pan
    function applyTransform() {
        const t = `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`;
        nodesLayer.style.transform = t;
        edgesLayer.style.transform = t;
        updateMinimapViewport();
    }

    function zoom(delta) {
        const newScale = Math.max(CONFIG.zoom.min, Math.min(CONFIG.zoom.max, transform.scale + delta));
        if (newScale !== transform.scale) {
            transform.x = transform.x + (canvas.width / 2) * (delta / transform.scale);
            transform.y = transform.y + (canvas.height / 2) * (delta / transform.scale);
            transform.scale = newScale;
            applyTransform();
            saveState();
        }
    }

    function resetView() {
        transform = { x: 0, y: 0, scale: CONFIG.zoom.initial };
        applyTransform();
        saveState();
    }

    // Dragging
    function startDrag(e) {
        if (e.target.closest('.topic-node') || e.target.closest('.phase-node')) return;

        isDragging = true;
        dragStart = { x: e.clientX, y: e.clientY };
        dragTransformStart = { x: transform.x, y: transform.y };
        viewport.style.cursor = 'grabbing';
    }

    function drag(e) {
        if (!isDragging) return;

        const dx = e.clientX - dragStart.x;
        const dy = e.clientY - dragStart.y;

        transform.x = dragTransformStart.x + dx;
        transform.y = dragTransformStart.y + dy;

        applyTransform();
        saveState();
    }

    function endDrag() {
        isDragging = false;
        viewport.style.cursor = 'grab';
    }

    // Minimap
    function updateMinimap() {
        if (!minimap || !minimapViewport) return;

        const viewportRect = viewport.getBoundingClientRect();
        const scale = 0.1; // Minimap scale

        minimapViewport.style.width = (viewportRect.width * scale) + 'px';
        minimapViewport.style.height = (viewportRect.height * scale) + 'px';
        minimapViewport.style.left = (-transform.x * scale) + 'px';
        minimapViewport.style.top = (-transform.y * scale) + 'px';
    }

    function updateMinimapViewport() {
        updateMinimap();
    }

    // Phase focus
    function focusPhase(phaseNum) {
        // Find all topic nodes in this phase
        const phaseNodes = Array.from(nodeMap.values()).filter(node => {
            const nodePhase = parseInt(node.dataset.phase);
            return nodePhase === phaseNum;
        });

        if (phaseNodes.length === 0) return;

        // Calculate bounds
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        phaseNodes.forEach(node => {
            const rect = node.getBoundingClientRect();
            const canvasX = parseFloat(node.style.left) + CONFIG.node.width/2;
            const canvasY = parseFloat(node.style.top) + CONFIG.node.height/2;

            minX = Math.min(minX, canvasX - CONFIG.node.width);
            minY = Math.min(minY, canvasY - CONFIG.node.height);
            maxX = Math.max(maxX, canvasX + CONFIG.node.width);
            maxY = Math.max(maxY, canvasY + CONFIG.node.height);
        });

        const phaseWidth = maxX - minX;
        const phaseHeight = maxY - minY;

        // Center on this phase
        const viewportWidth = viewport.clientWidth;
        const viewportHeight = viewport.clientHeight;

        transform.x = -(minX + phaseWidth/2 - viewportWidth/2);
        transform.y = -(minY + phaseHeight/2 - viewportHeight/2);
        transform.scale = CONFIG.zoom.initial;

        applyTransform();
        saveState();
    }

    // Legend
    function buildLegend() {
        if (!legendContainer) return;

        legendContainer.innerHTML = `
            <div class="legend-item"><span class="legend-color" style="background: ${CONFIG.colors.phase1}"></span> Foundation</div>
            <div class="legend-item"><span class="legend-color" style="background: ${CONFIG.colors.phase2}"></span> Core Skills</div>
            <div class="legend-item"><span class="legend-color" style="background: ${CONFIG.colors.phase3}"></span> Build & Practice</div>
            <div class="legend-item"><span class="legend-color" style="background: ${CONFIG.colors.phase4}"></span> Portfolio</div>
            <div class="legend-item"><span class="legend-color" style="background: ${CONFIG.colors.phase5}"></span> Job Prep</div>
            <div class="legend-item"><span class="legend-indicator completed"></span> Completed</div>
            <div class="legend-item"><span class="legend-indicator"></span> Not Started</div>
        `;
    }

    // Export
    function exportGraph(format) {
        if (format === 'json') {
            const data = {
                title: graphData.title,
                description: graphData.description,
                phases: graphData.sections.map(s => ({
                    phase: s.phase,
                    label: s.label,
                    topics: s.topics.map(t => ({
                        id: t.id,
                        label: t.label,
                        type: t.type,
                        importance: t.importance,
                        completed: completedTopics.has(t.id)
                    }))
                }))
            };

            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            downloadFile(blob, `${graphData.title.replace(/\s+/g, '_')}_roadmap.json`);
        } else if (format === 'png') {
            // Use html2canvas if available
            if (typeof html2canvas === 'undefined') {
                alert('Export to PNG requires html2canvas library. Add it to the page first.');
                return;
            }

            html2canvas(canvas).then(canvasImg => {
                const link = document.createElement('a');
                link.download = `${graphData.title.replace(/\s+/g, '_')}_roadmap.png`;
                link.href = canvasImg.toDataURL();
                link.click();
            });
        }
    }

    function downloadFile(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    // Fullscreen
    function toggleFullscreen() {
        const container = document.getElementById('graph-container');
        if (!document.fullscreenElement) {
            container.requestFullscreen().catch(err => {
                console.log('Fullscreen error:', err);
            });
        } else {
            document.exitFullscreen();
        }
    }

    // Keyboard shortcuts
    function handleKeydown(e) {
        // Ignore if user is typing in search or textarea
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;

        switch(e.key) {
            case '+':
            case '=':
                zoom(CONFIG.zoom.step);
                break;
            case '-':
                zoom(-CONFIG.zoom.step);
                break;
            case '0':
                resetView();
                break;
            case 'f':
                toggleFullscreen();
                break;
            case 'Escape':
                closePanel();
                break;
            case '/':
                e.preventDefault();
                searchInput.focus();
                break;
        }
    }

    // State persistence
    function saveState() {
        const state = {
            transform,
            selectedNode: selectedNode?.id,
            completedTopics: Array.from(completedTopics)
        };
        localStorage.setItem('skillsync_graph_state', JSON.stringify(state));
    }

    function loadSavedState() {
        try {
            const saved = localStorage.getItem('skillsync_graph_state');
            if (saved) {
                const state = JSON.parse(saved);

                // Restore transform
                if (state.transform) {
                    transform = state.transform;
                }

                // Restore completed topics
                if (state.completedTopics) {
                    completedTopics = new Set(state.completedTopics);
                }
            }
        } catch (e) {
            console.log('No saved state found');
        }
    }

    function saveCompletedTopics() {
        localStorage.setItem('skillsync_completed_topics', JSON.stringify(Array.from(completedTopics)));
    }

    function loadCompletedTopics() {
        try {
            const saved = localStorage.getItem('skillsync_completed_topics');
            if (saved) {
                completedTopics = new Set(JSON.parse(saved));
                // Update node styles
                completedTopics.forEach(id => {
                    const node = nodeMap.get(id);
                    if (node) node.classList.add('completed');
                });
            }
        } catch (e) {
            console.log('No completed topics saved');
        }
    }

    // Utility functions
    function hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : '100, 100, 100';
    }

    function getResourceIcon(type) {
        const icons = {
            youtube: '▶',
            udemy: '🎓',
            course: '📚',
            article: '📄',
            docs: '📘',
            project: '🛠',
            default: '🔗'
        };
        return icons[type] || icons.default;
    }

    function animateEntrance() {
        const nodes = Array.from(nodesLayer.children);
        nodes.forEach((node, idx) => {
            node.style.opacity = '0';
            node.style.transform += ' translateY(20px)';

            setTimeout(() => {
                node.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                node.style.opacity = '1';
                node.style.transform = node.style.transform.replace(' translateY(20px)', '');
            }, 50 + idx * 30);
        });
    }

    function closePanel() {
        const panel = document.getElementById('topic-detail-panel');
        if (panel) panel.classList.remove('active');
        selectedNode = null;
        document.querySelectorAll('.topic-node.selected').forEach(n => n.classList.remove('selected'));
    }

    function setupEventListeners() {
        // Mouse events for panning
        viewport.addEventListener('mousedown', startDrag);
        window.addEventListener('mousemove', drag);
        window.addEventListener('mouseup', endDrag);

        // Touch events for mobile
        viewport.addEventListener('touchstart', (e) => {
            if (e.touches.length === 1) {
                startDrag(e.touches[0]);
            }
        });
        viewport.addEventListener('touchmove', (e) => {
            if (isDragging && e.touches.length === 1) {
                e.preventDefault();
                drag(e.touches[0]);
            }
        });
        viewport.addEventListener('touchend', endDrag);

        // Wheel zoom
        viewport.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? -CONFIG.zoom.step : CONFIG.zoom.step;
            zoom(delta);
        }, { passive: false });

        // Buttons
        zoomInBtn?.addEventListener('click', () => zoom(CONFIG.zoom.step));
        zoomOutBtn?.addEventListener('click', () => zoom(-CONFIG.zoom.step));
        resetBtn?.addEventListener('click', resetView);
        fullscreenBtn?.addEventListener('click', toggleFullscreen);

        // Search
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                performSearch(e.target.value);
            });
        }

        // Export
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                const format = prompt('Export format (json/png):', 'json');
                if (format === 'json' || format === 'png') {
                    exportGraph(format);
                }
            });
        }

        // Keyboard
        window.addEventListener('keydown', handleKeydown);

        // Window resize
        window.addEventListener('resize', updateMinimap);

        // Fullscreen change
        document.addEventListener('fullscreenchange', () => {
            isFullscreen = !!document.fullscreenElement;
            if (fullscreenBtn) {
                fullscreenBtn.textContent = isFullscreen ? '⛶' : '⛶';
            }
        });

        // Click outside to deselect
        viewport.addEventListener('click', (e) => {
            if (e.target === viewport || e.target === nodesLayer || e.target === edgesLayer) {
                closePanel();
            }
        });
    }

    // Wait for DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose for external use
    window.VisualGuide = {
        zoomIn: () => zoom(CONFIG.zoom.step),
        zoomOut: () => zoom(-CONFIG.zoom.step),
        reset: resetView,
        focusPhase,
        search: performSearch,
        exportJSON: () => exportGraph('json'),
        exportPNG: () => exportGraph('png'),
        toggleFullscreen,
        getCompletedCount: () => completedTopics.size,
        getTotalCount: () => nodeMap.size
    };

})();