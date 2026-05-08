/* ============================================================
   SkillSync Resources — Interactive JS
   ============================================================ */

(function () {
  'use strict';

  /* ── Helpers ──────────────────────────────────────────────── */
  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

  /* ── Only run on Resources Index page ───────────────────── */
  const isIndex = !!$('#resource-search');
  const isDetail = !!$('.platforms-grid');

  /* ==========================================================
     INDEX PAGE
     ========================================================== */
  if (isIndex) {
    const searchInput   = $('#resource-search');
    const searchClear   = $('#search-clear');
    const clearSearchBtn = $('#clear-search-btn');
    const noResults     = $('#no-results');
    const sections      = $$('.res-category-section');
    const allCards      = $$('.course-card');
    const pillBar       = $('#category-filter-bar');
    const pills         = $$('.category-pill', pillBar);

    let activeCategory  = 'all';
    let searchQuery     = '';

    /* ── Filter Logic ──────────────────────────────────────── */
    function applyFilters() {
      let visibleTotal = 0;

      sections.forEach(section => {
        const catId   = section.dataset.category;
        const cards   = $$('.course-card', section);

        // Should this section show at all?
        const catMatch = activeCategory === 'all' || activeCategory === catId;

        let sectionVisible = 0;

        cards.forEach(card => {
          const titleMatch = card.dataset.title.includes(searchQuery);
          const tagsMatch  = card.dataset.tags.includes(searchQuery);
          const descMatch  = card.dataset.desc.includes(searchQuery);
          const textMatch  = !searchQuery || titleMatch || tagsMatch || descMatch;
          const show       = catMatch && textMatch;

          card.classList.toggle('hidden', !show);
          if (show) sectionVisible++;
        });

        section.classList.toggle('hidden', sectionVisible === 0);
        visibleTotal += sectionVisible;
      });

      // No-results state
      noResults.style.display = visibleTotal === 0 ? 'block' : 'none';
    }

    /* ── Search ────────────────────────────────────────────── */
    searchInput.addEventListener('input', () => {
      searchQuery = searchInput.value.toLowerCase().trim();
      searchClear.style.display = searchQuery ? 'flex' : 'none';
      applyFilters();
    });

    const clearSearch = () => {
      searchInput.value = '';
      searchQuery = '';
      searchClear.style.display = 'none';
      applyFilters();
      searchInput.focus();
    };

    searchClear.addEventListener('click', clearSearch);
    if (clearSearchBtn) clearSearchBtn.addEventListener('click', clearSearch);

    /* ── Category Pills ────────────────────────────────────── */
    pills.forEach(pill => {
      pill.addEventListener('click', () => {
        const cat = pill.dataset.category;

        // Update active pill
        pills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');

        if (cat === activeCategory && cat !== 'all') {
          // Toggle off — click same pill again resets to all
          activeCategory = 'all';
          $('#pill-all').classList.add('active');
          pill.classList.remove('active');
        } else {
          activeCategory = cat;
        }

        applyFilters();

        // Smooth scroll to section if filtering to one category
        if (activeCategory !== 'all') {
          const target = $(`#section-${activeCategory}`);
          if (target) {
            setTimeout(() => {
              target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 50);
          }
        }
      });
    });

    /* ── Staggered Card Entrance (IntersectionObserver) ─────── */
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry, i) => {
          if (entry.isIntersecting) {
            entry.target.style.animationDelay = `${i * 0.06}s`;
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: '0px 0px -40px 0px' }
    );

    allCards.forEach(card => observer.observe(card));

    /* ── Keyboard Shortcut: "/" focuses search ─────────────── */
    document.addEventListener('keydown', e => {
      if (
        e.key === '/' &&
        document.activeElement !== searchInput
      ) {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }
      if (e.key === 'Escape') {
        clearSearch();
      }
    });

    /* ── Search placeholder hint ────────────────────────────── */
    searchInput.setAttribute('placeholder', 'Search courses, topics, or tags…  (Press "/" to focus)');
  }

  /* ==========================================================
     DETAIL PAGE — animated entrance for platform cards
     ========================================================== */
  if (isDetail) {
    const platformCards = $$('.platform-card');

    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );

    platformCards.forEach((card, i) => {
      // Initial state (CSS animation handles entrance)
      observer.observe(card);
    });

    /* ── "Open Course" button ripple effect ─────────────────── */
    $$('.platform-cta').forEach(btn => {
      btn.addEventListener('click', function (e) {
        const ripple = document.createElement('span');
        ripple.style.cssText = `
          position: absolute;
          border-radius: 50%;
          background: rgba(255,255,255,0.3);
          width: 100px; height: 100px;
          margin-top: -50px; margin-left: -50px;
          top: ${e.offsetY}px; left: ${e.offsetX}px;
          animation: ripple 0.6s linear;
          pointer-events: none;
        `;
        this.style.position = 'relative';
        this.style.overflow = 'hidden';
        this.appendChild(ripple);
        setTimeout(() => ripple.remove(), 600);
      });
    });

    // Add ripple keyframe if not present
    if (!document.querySelector('#ripple-style')) {
      const style = document.createElement('style');
      style.id = 'ripple-style';
      style.textContent = `
        @keyframes ripple {
          from { transform: scale(0); opacity: 1; }
          to   { transform: scale(3); opacity: 0; }
        }
      `;
      document.head.appendChild(style);
    }
  }

})();
