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
      flowOpacity:     opts.flowOpacity     ?? 0.62,
      branchOpacity:   opts.branchOpacity   ?? 0.5,
      dotRadius:       opts.dotRadius       ?? 4,
      arrowSize:       opts.arrowSize       ?? 7,
      neonFlow:        opts.neonFlow        ?? false,
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
      .rm-neon-glow {
        stroke-linecap: round;
        stroke-linejoin: round;
        filter: url(#rm-neon-blur);
        pointer-events: none;
      }
      .rm-neon-pulse {
        stroke-linecap: round;
        stroke-linejoin: round;
        filter: url(#rm-neon-sharp);
        stroke-dasharray: 22 190;
        animation: rm-neon-flow var(--flowDur, 2.8s) linear infinite;
        pointer-events: none;
      }
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
      @keyframes rm-neon-flow {
        from { stroke-dashoffset: var(--flowStart, 220); }
        to { stroke-dashoffset: var(--flowEnd, -220); }
      }
      @media (prefers-reduced-motion: reduce) {
        .rm-neon-pulse,
        .rm-path-flow,
        .rm-path-branch,
        .rm-dot {
          animation: none;
        }
      }
    `;
    defs.appendChild(style);

    const blur = this._el('filter', {
      id: 'rm-neon-blur',
      x: '-35%',
      y: '-35%',
      width: '170%',
      height: '170%',
    });
    blur.appendChild(this._el('feGaussianBlur', {
      in: 'SourceGraphic',
      stdDeviation: '4',
      result: 'blur',
    }));
    const merge = this._el('feMerge');
    merge.appendChild(this._el('feMergeNode', { in: 'blur' }));
    merge.appendChild(this._el('feMergeNode', { in: 'SourceGraphic' }));
    blur.appendChild(merge);
    defs.appendChild(blur);

    const sharp = this._el('filter', {
      id: 'rm-neon-sharp',
      x: '-20%',
      y: '-20%',
      width: '140%',
      height: '140%',
    });
    sharp.appendChild(this._el('feGaussianBlur', {
      in: 'SourceGraphic',
      stdDeviation: '1.2',
      result: 'soft',
    }));
    const sharpMerge = this._el('feMerge');
    sharpMerge.appendChild(this._el('feMergeNode', { in: 'soft' }));
    sharpMerge.appendChild(this._el('feMergeNode', { in: 'SourceGraphic' }));
    sharp.appendChild(sharpMerge);
    defs.appendChild(sharp);

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

    if (this.opts.neonFlow) {
      this._appendNeonGlow(d, color, this.opts.flowStrokeW + 6, 0.24);
    }

    const path = this._el('path', {
      d,
      fill:               'none',
      stroke:             color,
      'stroke-width':     this.opts.flowStrokeW,
      opacity:            this.opts.flowOpacity,
      'stroke-dasharray': '7 7',
      'marker-end':       `url(#arrow-${this._phaseNum(from)})`,
      class:              this.opts.animatePaths ? 'rm-path-flow' : '',
      style:              `animation-delay:${delay}s`,
    });
    this.svg.appendChild(path);

    if (this.opts.neonFlow) {
      this._appendNeonPulse(d, color, this.opts.flowStrokeW + 1.4, delay, '2.9s', '260', '-260');
    }
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
    if (this.opts.neonFlow) {
      this._appendNeonGlow(d, color, this.opts.branchStrokeW + 5, 0.2);
    }
    this.svg.appendChild(path);

    if (this.opts.neonFlow) {
      const directionStart = side === 'left' ? '-220' : '220';
      const directionEnd = side === 'left' ? '220' : '-220';
      this._appendNeonPulse(d, color, this.opts.branchStrokeW + 1.3, delay + 0.12, '2.35s', directionStart, directionEnd);
    }

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

  _appendNeonGlow(d, color, width, opacity) {
    const glow = this._el('path', {
      d,
      fill: 'none',
      stroke: color,
      'stroke-width': width,
      opacity,
      class: 'rm-neon-glow',
    });
    this.svg.appendChild(glow);
  }

  _appendNeonPulse(d, color, width, delay, duration, start, end) {
    const pulse = this._el('path', {
      d,
      fill: 'none',
      stroke: color,
      'stroke-width': width,
      opacity: '0.92',
      class: 'rm-neon-pulse',
      style: `animation-delay:${delay}s;--flowDur:${duration};--flowStart:${start};--flowEnd:${end};`,
    });
    this.svg.appendChild(pulse);
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
