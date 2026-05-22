/**
 * RoadmapLayoutEngine
 *
 * Computes the roadmap.sh-style visual guide layout: section nodes sit on
 * a central vertical spine and topic nodes fan out to the left and right.
 * This file only returns positioned data; renderers own the DOM/SVG work.
 */

class RoadmapLayoutEngine {
  /**
   * @param {Array} sections - guide_data.sections from the AI
   * @param {Object} opts - optional layout overrides
   */
  constructor(sections, opts = {}) {
    this.sections = sections || [];
    this.C = {
      canvasWidth: opts.canvasWidth ?? 960,
      secNodeW: opts.secNodeW ?? 236,
      secNodeH: opts.secNodeH ?? 48,
      topicNodeW: opts.topicNodeW ?? 218,
      topicNodeH: opts.topicNodeH ?? 44,
      topicHGap: opts.topicHGap ?? 96,
      topicVGap: opts.topicVGap ?? 14,
      sectionVGap: opts.sectionVGap ?? 66,
      startY: opts.startY ?? 24,
    };
    this.centerX = this.C.canvasWidth / 2;
  }

  /**
   * Compute the full layout.
   * @returns {{ nodes: Array, edges: Array, totalHeight: number, canvasWidth: number }}
   */
  compute() {
    const nodes = [];
    const edges = [];
    const secIds = {};
    let curY = this.C.startY;

    this.sections.forEach((sec, si) => {
      const phase = this._phase(sec.phase);
      const topics = sec.topics || [];
      const explicitLeft = topics.filter((t) => String(t.side || '').toLowerCase() === 'left');
      const explicitRight = topics.filter((t) => String(t.side || '').toLowerCase() === 'right');
      const unsided = topics.filter((t) => !['left', 'right'].includes(String(t.side || '').toLowerCase()));
      const leftT = explicitLeft.concat(unsided.filter((_, i) => i % 2 === 0));
      const rightT = explicitRight.concat(unsided.filter((_, i) => i % 2 === 1));
      const leftHeights = leftT.map((t) => this._estimateTopicHeight(t.label || ''));
      const rightHeights = rightT.map((t) => this._estimateTopicHeight(t.label || ''));
      const leftBlockH = this._columnBlockHeight(leftHeights);
      const rightBlockH = this._columnBlockHeight(rightHeights);
      const topicBlockH = Math.max(leftBlockH, rightBlockH, 0);
      const laneH = Math.max(this.C.secNodeH, topicBlockH);
      const secId = sec.id || `sec_${si}`;
      const secY = curY + (laneH - this.C.secNodeH) / 2;
      const topicBaseY = curY + (laneH - topicBlockH) / 2;

      secIds[si] = secId;

      nodes.push(this._makeNode({
        id: secId,
        kind: 'section',
        label: sec.label || '',
        x: this.centerX - this.C.secNodeW / 2,
        y: secY,
        w: this.C.secNodeW,
        h: this.C.secNodeH,
        phase,
        meta: { order: si, section: sec },
      }));

      if (si > 0) {
        edges.push(this._makePhaseEdge(secIds[si - 1], secId, phase));
      }

      const leftX = this.centerX - this.C.secNodeW / 2 - this.C.topicHGap - this.C.topicNodeW;
      const rightX = this.centerX + this.C.secNodeW / 2 + this.C.topicHGap;

      let leftY = topicBaseY;
      leftT.forEach((t, i) => {
        const h = leftHeights[i];
        const tn = this._makeTopicNode(t, `${secId}_l${i}`, leftX, leftY, i, 'left', phase, secId, sec.label || '', h);
        nodes.push(tn);
        edges.push(this._makeTopicEdge(secId, tn.id, 'left', phase));
        leftY += h + this.C.topicVGap;
      });

      let rightY = topicBaseY;
      rightT.forEach((t, i) => {
        const h = rightHeights[i];
        const tn = this._makeTopicNode(t, `${secId}_r${i}`, rightX, rightY, i, 'right', phase, secId, sec.label || '', h);
        nodes.push(tn);
        edges.push(this._makeTopicEdge(secId, tn.id, 'right', phase));
        rightY += h + this.C.topicVGap;
      });

      curY += laneH + this.C.sectionVGap;
    });

    return {
      nodes,
      edges,
      totalHeight: curY + 60,
      canvasWidth: this.C.canvasWidth,
    };
  }

  _phase(raw) {
    const p = parseInt(raw);
    return (p >= 1 && p <= 5) ? p : 1;
  }

  _makeNode({ id, kind, label, x, y, w, h, phase, meta = {} }) {
    return {
      id, kind, label, x, y, w, h, phase, meta,
      cx: x + w / 2,
      cy: y + h / 2,
    };
  }

  _estimateTopicHeight(label) {
    const text = String(label || '').trim();
    const innerW = this.C.topicNodeW - 28;
    const charsPerLine = Math.max(14, Math.floor(innerW / 7.4));
    const lines = Math.min(3, Math.max(1, Math.ceil(text.length / charsPerLine)));
    return Math.max(this.C.topicNodeH, lines * 19 + 14);
  }

  _columnBlockHeight(heights) {
    if (!heights.length) return 0;
    return heights.reduce((sum, h, i) => sum + h + (i > 0 ? this.C.topicVGap : 0), 0);
  }

  _makeTopicNode(topic, id, colX, y, rowIndex, side, phase, sectionId, sectionLabel, height) {
    const h = height || this.C.topicNodeH;
    return this._makeNode({
      id,
      kind: 'topic',
      label: topic.label || '',
      x: colX,
      y,
      w: this.C.topicNodeW,
      h,
      phase,
      meta: {
        topicType: topic.type || 'required',
        importance: topic.importance || 'important',
        side,
        sectionId,
        sectionLabel: topic.section_label || sectionLabel,
        raw: topic,
      },
    });
  }

  _makePhaseEdge(fromId, toId, toPhase) {
    return { id: `e_${fromId}_${toId}`, fromId, toId, kind: 'phase-flow', phase: toPhase };
  }

  _makeTopicEdge(fromId, toId, side, phase) {
    return { id: `e_${fromId}_${toId}`, fromId, toId, kind: 'section-topic', side, phase };
  }
}

const PhaseColors = {
  1: { hex: '#10b981', rgb: '16,185,129', name: 'Foundation', desc: 'Build your basics' },
  2: { hex: '#3b82f6', rgb: '59,130,246', name: 'Core Skills', desc: 'Strengthen core skills' },
  3: { hex: '#f97316', rgb: '249,115,22', name: 'Build', desc: 'Build practical skills' },
  4: { hex: '#8b5cf6', rgb: '139,92,246', name: 'Portfolio', desc: 'Showcase your work' },
  5: { hex: '#ef4444', rgb: '239,68,68', name: 'Job Prep', desc: 'Get ready for jobs' },
};

function getPhaseColor(phase) {
  return PhaseColors[parseInt(phase)] || PhaseColors[1];
}
