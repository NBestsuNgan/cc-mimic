/* ============================================
   FINAL FANTASY VI - Interactive Script
   ============================================ */

// ---- Starry background ----
(function initStars() {
    const container = document.getElementById('stars');
    if (!container) return;
    for (let i = 0; i < 100; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left             = Math.random() * 100 + '%';
        star.style.top              = Math.random() * 100 + '%';
        star.style.animationDelay   = Math.random() * 2 + 's';
        star.style.width            = Math.random() * 2 + 1 + 'px';
        star.style.height           = star.style.width;
        container.appendChild(star);
    }
})();

// ---- Navigation ----
(function initNav() {
    const navBtns   = document.querySelectorAll('.nav-btn');
    const sections  = document.querySelectorAll('.section');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            btn.style.transform = 'scale(0.95)';
            setTimeout(() => btn.style.transform = '', 100);

            navBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const sectionId = btn.dataset.section;
            sections.forEach(s => s.classList.remove('active'));
            document.getElementById(sectionId).classList.add('active');

            // 10 % random encounter flash
            if (Math.random() < 0.1) triggerEncounter();
        });
    });
})();

// ---- Character cards ----
(function initCharCards() {
    const charCards    = document.querySelectorAll('.char-card.char-card'); // keep default
    const charDetails  = document.querySelectorAll('.char-detail');

    // Handle both old-style .char-card and any card in #characters section
    const allCharCards = document.querySelectorAll('#characters .char-card');

    allCharCards.forEach(card => {
        card.addEventListener('click', () => {
            const charId       = card.dataset.char;
            const detailPanel  = document.getElementById(charId + '-detail');

            charDetails.forEach(d => d.classList.remove('visible'));
            allCharCards.forEach(c => c.classList.remove('selected'));

            if (detailPanel) {
                detailPanel.classList.add('visible');
                card.classList.add('selected');
            }
        });
    });
})();

// ---- Summon (Esper) cards ----
(function initSummonCards() {
    const summonCards   = document.querySelectorAll('.summon-card');
    const summonDetails = document.querySelectorAll('.summon-detail');

    summonCards.forEach(card => {
        card.addEventListener('click', () => {
            const summonId     = card.dataset.summon;
            const detailPanel  = document.getElementById(summonId + '-detail');

            summonDetails.forEach(d => d.classList.remove('visible'));
            summonCards.forEach(c => c.classList.remove('selected'));

            if (detailPanel) {
                detailPanel.classList.add('visible');
                card.classList.add('selected');
                triggerSummonFlash();
            }
        });
    });
})();

// ---- Summon element filters ----
(function initSummonFilters() {
    const filterBtns = document.querySelectorAll('.filter-btn');
    const summonCards = document.querySelectorAll('.summon-card');

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const filter = btn.dataset.filter;

            summonCards.forEach(card => {
                if (filter === 'all') {
                    card.style.display = '';
                } else {
                    card.classList.contains(filter + '-card')
                        ? card.style.display = ''
                        : card.style.display = 'none';
                }
            });
        });
    });
})();

// ---- Effects ----
function triggerEncounter() {
    const flash = document.getElementById('encounterFlash');
    if (!flash) return;
    flash.classList.add('active');
    setTimeout(() => flash.classList.remove('active'), 300);
}

function triggerSummonFlash() {
    const flash = document.getElementById('summonFlash');
    if (!flash) return;
    flash.classList.add('active');
    setTimeout(() => flash.classList.remove('active'), 600);
}

function showSecret(message) {
    const notification = document.getElementById('secretNotification');
    const secretText   = document.getElementById('secretText');
    if (!notification || !secretText) return;
    secretText.textContent = message;
    notification.classList.add('show');
    setTimeout(() => notification.classList.remove('show'), 3000);
}

// ---- Konami code easter egg ----
(function initKonami() {
    const code = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown',
                  'ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];
    let index = 0;

    document.addEventListener('keydown', (e) => {
        if (e.key === code[index]) {
            index++;
            if (index === code.length) {
                showSecret('KONAMI CODE ACTIVATED! - All Espers Unlocked!');
                triggerEncounter();
                triggerEncounter();
                index = 0;
            }
        } else {
            index = 0;
        }
    });
})();

// ---- Logo click easter egg ----
(function initLogoEgg() {
    let clickCount = 0;
    const logo = document.querySelector('.ff-logo');
    if (!logo) return;

    logo.addEventListener('click', () => {
        clickCount++;
        if (clickCount >= 5) {
            showSecret('You found the hidden developer message!');
            clickCount = 0;
        }
    });
})();

// ---- Kefka double-click easter egg ----
(function initKefkaEgg() {
    const kefkaCard = document.querySelector('[data-char="kefka"]');
    if (!kefkaCard) return;

    kefkaCard.addEventListener('dblclick', () => {
        showSecret('KEFKA: WAHAHAHA! Foolish mortals!');
        triggerEncounter();
    });
})();

// ---- Stat bar animation on scroll ----
(function initStatObserver() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.querySelectorAll('.stat-fill').forEach(stat => {
                    const width = stat.style.width;
                    stat.style.width = '0%';
                    setTimeout(() => stat.style.width = width, 100);
                });
            }
        });
    }, { threshold: 0.5 });

    document.querySelectorAll('.rpg-box').forEach(box => observer.observe(box));
})();

// ---- Floating sprite animation ----
(function initSpriteFloat() {
    document.querySelectorAll('.char-sprite').forEach((sprite, i) => {
        sprite.style.animation = `float ${2 + i * 0.2}s ease-in-out infinite`;
        sprite.style.animationDelay = `${i * 0.1}s`;
    });
})();

// ---- Cursor blink via setInterval ----
(function initCursor() {
    const cursor = document.querySelector('.cursor');
    if (!cursor) return;
    setInterval(() => {
        cursor.style.opacity = cursor.style.opacity === '0' ? '1' : '0';
    }, 500);
})();

// ---- Console welcome ----
console.log(
    '%c FINAL FANTASY VI ',
    'background: #2d1b4e; color: #ffd700; font-size: 20px; padding: 10px;'
);
console.log('%c Welcome, Returner! Look for secrets… ', 'color: #aaa;');
