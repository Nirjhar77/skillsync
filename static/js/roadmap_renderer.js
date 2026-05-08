/**
 * RoadmapSVGRenderer
 * ─────────────────────────────────────────────────────────────────────────────
 * Consumes a layout object produced by RoadmapLayoutEngine and renders:
 *   • SVG <defs>  — arrowhead markers, animated gradient strokes
 *   • Phase-flow edges  — animated bezier curves between section nodes
 *   • Section-topic edges — dashed bezier branches to topic nodes
 *   • Entry-dot circles where edges meet topic nodes
 *
 * Usage:
 *   const layout   = new RoadmapLayoutEngine(sections).compute();
 *   const renderer = new RoadmapSVGRenderer(svgEl, layout);
 *   renderer.render();
 * ─────────────────────────────────────────────────────────────────────────────
 */

class RoadmapSVGRenderer {
  /**
   * @param {SVGSVGElement} svgEl   - the <svg> element to draw into
   * @param {Object}        layout  - output of RoadmapLayoutEngine.compute()
   * @param {Object}        opts    - optional rendering tweaks
   */
  constructor(svgEl, layout, opts = {}) {
    this.svg    = svgEl;
    this.layout = layout;
    this.opts   = {
      animatePaths:    opts.animatePaths    ?? true,
      animDuration:    opts.animDuration    ?? '0.7s',
      flowStrokeW:     opts.flowStrokeW     ?? 2.5,
      branchStrokeW:   opts.branchStrokeW   ?? 1.6,
      flowOpacity:     opts.flowOpacity     ?? 0.55,
      branchOpacity:   opts.branchOpacity   ?? 0.45,
      dotRadius:       opts.dotRadius       ?? 4,
      arrowSize:       opts.arrowSize       ?? 7,
    };
  }

  // ─── Public ────────────────────────────────────────────────────────────────

  render() {
    this._resize();
    this.svg.innerHTML = '';           // clear previous paint
    this._appendDefs();
    this._renderEdges();
  }

  // ─── Private: sizing ───────────────────────────────────────────────────────

  _resize() {
    this.svg.setAttribute('width',  this.layout.canvasWidth);
    this.svg.setAttribute('height', this.layout.totalHeight);
  }

  // ─── Private: <defs> ───────────────────────────────────────────────────────

  _appendDefs() {
    const defs = this._el('defs');

    // One arrowhead marker per phase
    [1, 2, 3, 4, 5].forEach(p => {
      const { hex } = getPhaseColor(p);
      const marker  = this._el('marker', {
        id:           `arrow-${p}`,
        markerWidth:  this.opts.arrowSize,
        markerHeight: this.opts.arrowSize,
        refX:         this.opts.arrowSize - 1,
        refY:         this.opts.arrowSize / 2,
        orient:       'auto',
        markerUnits:  'userSpaceOnUse',
      });
      const path = this._el('path', {
        d:    `M0,0 L0,${this.opts.arrowSize} L${this.opts.arrowSize},${this.opts.arrowSize / 2} z`,
        fill: hex,
      });
      marker.appendChild(path);
      defs.appendChild(marker);
    });

    // Animated dot pulse for entry-dots (optional decoration)
    const style = this._el('style');
    style.textContent = `
      .rm-path-flow {
        stroke-dasharray: 2000;
        stroke-dashoffset: 2000;
        animation: rm-draw var(--dur, 0.7s) ease forwards;
      }
      .rm-path-branch {
        stroke-dasharray: 300;
        stroke-dashoffset: 300;
        animation: rm-draw var(--dur, 0.5s) ease forwards;
      }
      .rm-dot {
        opacity: 0;
        animation: rm-pop 0.3s ease forwards;
      }
      @keyframes rm-draw {
        to { stroke-dashoffset: 0; }
      }
      @keyframes rm-pop {
        to { opacity: 0.8; }
      }
    `;
    defs.appendChild(style);
    this.svg.appendChild(defs);
  }

  // ─── Private: edges ────────────────────────────────────────────────────────

  _renderEdges() {
    const nodeMap = this._buildNodeMap();
    let   delay   = 0;   // staggered animation delays (seconds)

    this.layout.edges.forEach(edge => {
      const from = nodeMap[edge.fromId];
      const to   = nodeMap[edge.toId];
      if (!from || !to) return;

      const { hex } = getPhaseColor(edge.phase || from.phase || 1);

      if (edge.kind === 'phase-flow') {
        this._renderFlowEdge(from, to, hex, delay);
        delay += 0.06;
      } else if (edge.kind === 'section-topic') {
        this._renderBranchEdge(from, to, edge.side, hex, delay);
        delay += 0.04;
      }
    });
  }

  /**
   * Vertical bezier between two consecutive section nodes.
   * Exits from the bottom-center of `from`, enters the top-center of `to`.
   */
  _renderFlowEdge(from, to, color, delay) {
    const x1 = from.cx;
    const y1 = from.y + from.h;
    const x2 = to.cx;
    const y2 = to.y;
    const d = `M${x1},${y1} L${x2},${y2}`;

    const path = this._el('path', {
      d,
      fill:               'none',
      stroke:             color,
      'stroke-width':     this.opts.flowStrokeW,
      opacity:            this.opts.flowOpacity,
      'stroke-dasharray': '7 7',
      'marker-end':       `url(#arrow-${this._phaseNum(from)})`,
      class:              '',
      style:              `animation-delay:${delay}s`,
    });
    this.svg.appendChild(path);
  }

  /**
   * Horizontal bezier from section side-edge → topic node center.
   * Uses a cubic bezier with control points that create a smooth elbow.
   */
  _renderBranchEdge(fromSec, toTopic, side, color, delay) {
    const sx = side === 'left'
      ? fromSec.x
      : fromSec.x + fromSec.w;
    const sy = fromSec.cy;

    const tx = side === 'left'
      ? toTopic.x + toTopic.w
      : toTopic.x;
    const ty = toTopic.cy;

    const cpMidX = (sx + tx) / 2;
    const d = Math.abs(sy - ty) < 2
      ? `M${sx},${sy} L${tx},${ty}`
      : `M${sx},${sy} C${cpMidX},${sy} ${cpMidX},${ty} ${tx},${ty}`;

    const path = this._el('path', {
      d,
      fill:              'none',
      stroke:            color,
      'stroke-width':    this.opts.branchStrokeW,
      'stroke-dasharray':'3 5',
      opacity:           this.opts.branchOpacity,
      class:             this.opts.animatePaths ? 'rm-path-branch' : '',
      style:             `--dur:0.45s;animation-delay:${delay}s`,
    });
    this.svg.appendChild(path);

    // Entry dot where the path meets the topic node
    const dot = this._el('circle', {
      cx:    tx,
      cy:    ty,
      r:     this.opts.dotRadius,
      fill:  color,
      class: this.opts.animatePaths ? 'rm-dot' : '',
      style: `animation-delay:${delay + 0.3}s`,
    });
    this.svg.appendChild(dot);
  }

  // ─── Utilities ─────────────────────────────────────────────────────────────

  /** Build a fast id → node lookup map. */
  _buildNodeMap() {
    const map = {};
    this.layout.nodes.forEach(n => { map[n.id] = n; });
    return map;
  }

  /** Extract phase number from a node. */
  _phaseNum(node) {
    return parseInt(node.phase) || 1;
  }

  /**
   * Create an SVG element with attributes.
   * @param {string} tag
   * @param {Object} attrs
   */
  _el(tag, attrs = {}) {
    const ns  = 'http://www.w3.org/2000/svg';
    const el  = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
    return el;
  }
}
