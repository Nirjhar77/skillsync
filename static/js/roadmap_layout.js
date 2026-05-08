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
      topicNodeH: opts.topicNodeH ?? 40,
      topicHGap: opts.topicHGap ?? 96,
      topicVGap: opts.topicVGap ?? 9,
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
      const maxRows = Math.max(leftT.length, rightT.length, 0);
      const topicBlockH = maxRows > 0
        ? maxRows * this.C.topicNodeH + Math.max(0, maxRows - 1) * this.C.topicVGap
        : 0;
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

      leftT.forEach((t, i) => {
        const tn = this._makeTopicNode(t, `${secId}_l${i}`, leftX, topicBaseY, i, 'left', phase, secId, sec.label || '');
        nodes.push(tn);
        edges.push(this._makeTopicEdge(secId, tn.id, 'left', phase));
      });

      rightT.forEach((t, i) => {
        const tn = this._makeTopicNode(t, `${secId}_r${i}`, rightX, topicBaseY, i, 'right', phase, secId, sec.label || '');
        nodes.push(tn);
        edges.push(this._makeTopicEdge(secId, tn.id, 'right', phase));
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

  _makeTopicNode(topic, id, colX, baseY, rowIndex, side, phase, sectionId, sectionLabel) {
    const y = baseY + rowIndex * (this.C.topicNodeH + this.C.topicVGap);
    return this._makeNode({
      id,
      kind: 'topic',
      label: topic.label || '',
      x: colX,
      y,
      w: this.C.topicNodeW,
      h: this.C.topicNodeH,
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
  1: { hex: '#16a34a', rgb: '22,163,74', name: 'Foundation' },
  2: { hex: '#0ea5e9', rgb: '14,165,233', name: 'Core Skills' },
  3: { hex: '#22c55e', rgb: '34,197,94', name: 'Build' },
  4: { hex: '#f59e0b', rgb: '245,158,11', name: 'Portfolio' },
  5: { hex: '#a855f7', rgb: '168,85,247', name: 'Job Prep' },
};

function getPhaseColor(phase) {
  return PhaseColors[parseInt(phase)] || PhaseColors[1];
}
