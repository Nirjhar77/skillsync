/**
 * SkillSync — Global JavaScript
 * Handles animations, scroll effects, and common UI interactions.
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- Intersection Observer for fade-in animations ---
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px',
    };

    const fadeObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                fadeObserver.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.glass-card, .career-card, .milestone-card, .tracker-item').forEach((el) => {
        fadeObserver.observe(el);
    });

    // --- Smooth scroll for anchor links ---
    document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // --- Add SVG gradient definitions for score rings ---
    addScoreGradient();

    // --- Navbar scroll effect ---
    const navbar = document.getElementById('main-nav');
    if (navbar) {
        let lastScroll = 0;
        window.addEventListener('scroll', () => {
            const currentScroll = window.pageYOffset;
            if (currentScroll > 10) {
                navbar.style.boxShadow = '0 4px 30px rgba(0, 0, 0, 0.3)';
            } else {
                navbar.style.boxShadow = 'none';
            }
            lastScroll = currentScroll;
        });
    }
});

/**
 * Add SVG gradient definition for score rings.
 * This creates a gradient that can be referenced by stroke="url(#scoreGradient)".
 */
function addScoreGradient() {
    const svgs = document.querySelectorAll('.score-svg');
    svgs.forEach((svg) => {
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
        gradient.setAttribute('id', 'scoreGradient');
        gradient.setAttribute('x1', '0%');
        gradient.setAttribute('y1', '0%');
        gradient.setAttribute('x2', '100%');
        gradient.setAttribute('y2', '0%');

        const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop1.setAttribute('offset', '0%');
        stop1.setAttribute('stop-color', '#00d4ff');

        const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop2.setAttribute('offset', '100%');
        stop2.setAttribute('stop-color', '#7c3aed');

        gradient.appendChild(stop1);
        gradient.appendChild(stop2);
        defs.appendChild(gradient);
        svg.insertBefore(defs, svg.firstChild);
    });
}

/**
 * Show a toast notification.
 */
function showToast(message, type = 'info') {
    let container = document.getElementById('flash-messages');
    if (!container) {
        container = document.createElement('div');
        container.id = 'flash-messages';
        container.className = 'flash-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `flash flash-${type}`;
    toast.innerHTML = `
        <span class="flash-text">${message}</span>
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="flash-close"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
    `;
    toast.onclick = () => toast.remove();
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}
