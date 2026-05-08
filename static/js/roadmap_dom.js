/**
 * RoadmapDOMRenderer
 * ─────────────────────────────────────────────────────────────────────────────
 * Consumes a layout object from RoadmapLayoutEngine and renders the
 * actual HTML nodes (section boxes, topic pills) into a container div.
 *
 * Keeps DOM writes separate from SVG path drawing (RoadmapSVGRenderer)
 * so each concern can be swapped independently.
 *
 * Usage:
 *   const layout = new RoadmapLayoutEngine(sections).compute();
 *   const dom    = new RoadmapDOMRenderer(containerEl, layout, { onTopicClick });
 *   dom.render();
 * ─────────────────────────────────────────────────────────────────────────────
 */

class RoadmapDOMRenderer {
  /**
   * @param {HTMLElement} container   - absolutely-positioned canvas div
   * @param {Object}      layout      - output of RoadmapLayoutEngine.compute()
   * @param {Object}      opts
   * @param {Function}    opts.onTopicClick  - called with (topicNode, domEl)
   */
  constructor(container, layout, opts = {}) {
    this.container = container;
    this.layout    = layout;
    this.opts      = opts;
    this._selected = null;   // currently selected topic DOM element
  }

  // ─── Public ────────────────────────────────────────────────────────────────

  render() {
    // Set canvas dimensions
    this.container.style.position = 'relative';
    this.container.style.width    = this.layout.canvasWidth + 'px';
    this.container.style.height   = this.layout.totalHeight + 'px';

    // Render every node
    this.layout.nodes.forEach((node, i) => {
      const el = node.kind === 'section'
        ? this._renderSection(node, i)
        : this._renderTopic(node, i);

      this.container.appendChild(el);
    });
  }

  /** Deselect the currently highlighted topic node. */
  clearSelection() {
    if (this._selected) {
      this._selected.classList.remove('rm-selected');
      this._applyIdleTopicStyle(this._selected);
      this._selected = null;
    }
  }

  // ─── Private: section node ─────────────────────────────────────────────────

  _renderSection(node, index) {
    const { hex, rgb } = getPhaseColor(node.phase);

    const el = document.createElement('div');
    el.className   = 'rm-section rm-neon-node';
    el.id          = `node-${node.id}`;
    el.dataset.id  = node.id;
    el.dataset.ph  = node.phase;
    el.textContent = node.label;

    // Position
    Object.assign(el.style, {
      position:   'absolute',
      left:       node.x + 'px',
      top:        node.y + 'px',
      width:      node.w + 'px',
      height:     node.h + 'px',
      '--ph-hex': hex,
      '--ph-rgb': rgb,
      background: `linear-gradient(180deg, rgba(${rgb},.18), rgba(${rgb},.05))`,
      border:     `2px solid ${hex}`,
      color:      '#fff',
      boxShadow:  `0 4px 15px rgba(${rgb},.22), 0 0 24px rgba(${rgb},.16), inset 0 0 12px rgba(${rgb},.1)`,
      fontFamily:      'Outfit, sans-serif',
      fontSize:        '.78rem',
      fontWeight:      '900',
      letterSpacing:   '0',
      textTransform:   'none',
      textAlign:       'center',
      display:         'flex',
      alignItems:      'center',
      justifyContent:  'center',
      borderRadius:    '8px',
      userSelect:      'none',
      zIndex:          '2',
      opacity:         '0',
      transform:       'translateY(4px)',
      animation:       `rmFadeUp .45s ease ${(index * 0.035).toFixed(2)}s forwards, rmNodeGlow 3.4s ease-in-out ${(index * 0.05).toFixed(2)}s infinite`,
    });

    return el;
  }

  // ─── Private: topic node ───────────────────────────────────────────────────

  _renderTopic(node, index) {
    const { hex, rgb } = getPhaseColor(node.phase);
    const { topicType, importance } = node.meta;

    const el = document.createElement('div');
    el.className = `rm-topic rm-neon-node rm-topic--${topicType} rm-topic--${importance}`;
    el.id          = `node-${node.id}`;
    el.dataset.id  = node.id;
    el.dataset.ph  = node.phase;

    // Build inner HTML — label + optional badge
    const optBadge = topicType === 'optional'
      ? `<span class="rm-opt-badge">opt</span>`
      : topicType === 'tool'
      ? `<span class="rm-tool-badge">tool</span>`
      : topicType === 'project'
      ? `<span class="rm-proj-badge">proj</span>`
      : '';
    el.innerHTML = `<span class="rm-node-label">${node.label}</span>${optBadge}`;

    // Base idle style
    Object.assign(el.style, {
      position:        'absolute',
      left:             node.x + 'px',
      top:              node.y + 'px',
      width:            node.w + 'px',
      minHeight:        node.h + 'px',
      // Store phase tokens for hover/select
      '--ph-hex':       hex,
      '--ph-rgb':       rgb,
      zIndex:           '3',
      // Reveal animation
      opacity:          '0',
      transform:        'translateY(8px)',
      animation:        `rmFadeUp .4s ease ${(index * 0.03).toFixed(2)}s forwards`,
    });

    this._applyIdleTopicStyle(el);

    // Hover effects
    el.addEventListener('mouseenter', () => {
      if (!el.classList.contains('rm-selected')) {
        el.style.borderColor = hex;
        el.style.boxShadow   = `0 0 14px rgba(${rgb},.28)`;
        el.style.color       = 'var(--text-primary, #f1f5f9)';
        el.style.transform   = 'translateY(-2px)';
      }
    });
    el.addEventListener('mouseleave', () => {
      if (!el.classList.contains('rm-selected')) {
        this._applyIdleTopicStyle(el);
        el.style.transform = 'none';
      }
    });

    // Click
    el.addEventListener('click', () => {
      this._selectTopic(el, node, hex, rgb);
      if (this.opts.onTopicClick) this.opts.onTopicClick(node, el);
    });

    return el;
  }

  // ─── Private: selection state ──────────────────────────────────────────────

  _selectTopic(el, node, hex, rgb) {
    // Deselect previous
    this.clearSelection();

    el.classList.add('rm-selected');
    el.style.borderColor = hex;
    el.style.boxShadow   = `0 0 20px rgba(${rgb},.35), inset 0 0 0 1px rgba(${rgb},.4)`;
    el.style.color       = '#fff';
    el.style.background  = `rgba(${rgb},.15)`;
    el.style.transform   = 'none';

    this._selected = el;
  }

  _applyIdleTopicStyle(el) {
    const importanceCls  = el.classList.contains('rm-topic--optional');
    const isOptional     = importanceCls;

    Object.assign(el.style, {
      background:   'rgba(255,255,255,.04)',
      borderWidth:  '1.5px',
      borderStyle:  isOptional ? 'dashed' : 'solid',
      borderColor:  'rgba(255,255,255,.72)',
      borderRadius: '7px',
      color:        'var(--text-primary, #f1f5f9)',
      boxShadow:    'none',
      cursor:       'pointer',
      display:      'flex',
      alignItems:   'center',
      justifyContent: 'center',
      gap:           '4px',
      padding:       '7px 12px',
      fontFamily:    'Inter, sans-serif',
      fontSize:      '.78rem',
      fontWeight:    '800',
      lineHeight:    '1.3',
      textAlign:     'center',
      backdropFilter:'none',
      transition:    'all .2s',
      opacity:       isOptional ? '.72' : '1',
    });
  }

  // ─── Static: inject required global CSS ───────────────────────────────────
  /**
   * Call once to inject the keyframes and badge styles needed by rendered nodes.
   * Idempotent — safe to call multiple times.
   */
  static injectStyles() {
    if (document.getElementById('rm-dom-styles')) return;
    const style = document.createElement('style');
    style.id    = 'rm-dom-styles';
    style.textContent = `
      @keyframes rmFadeUp {
        to { opacity: 1; transform: translateY(0); }
      }
      .rm-section {
        will-change: transform, opacity;
      }
      .rm-topic {
        will-change: transform, opacity;
        word-break: break-word;
      }
      .rm-neon-node {
        filter: drop-shadow(0 0 5px rgba(var(--ph-rgb), .18));
      }
      .rm-section.rm-neon-node {
        animation-name: rmFadeUp, rmNodeGlow;
        animation-duration: .45s, 3.4s;
        animation-timing-function: ease, ease-in-out;
        animation-iteration-count: 1, infinite;
        animation-fill-mode: forwards, none;
      }
      @keyframes rmNodeGlow {
        0%, 100% { filter: drop-shadow(0 0 4px rgba(var(--ph-rgb), .16)); }
        50% { filter: drop-shadow(0 0 11px rgba(var(--ph-rgb), .32)); }
      }
      .rm-node-label {
        flex: 1;
      }
      .rm-opt-badge, .rm-tool-badge, .rm-proj-badge {
        font-size: .58rem;
        font-weight: 700;
        padding: .05rem .32rem;
        border-radius: 3px;
        flex-shrink: 0;
      }
      .rm-opt-badge  { background: rgba(148,163,184,.18); color: #94a3b8; }
      .rm-tool-badge { background: rgba(251,191,36,.15);  color: #fbbf24; }
      .rm-proj-badge { background: rgba(52,211,153,.15);  color: #34d399; }
      @media (prefers-reduced-motion: reduce) {
        .rm-section.rm-neon-node {
          animation: rmFadeUp .45s ease forwards;
        }
      }
    `;
    document.head.appendChild(style);
  }
}
