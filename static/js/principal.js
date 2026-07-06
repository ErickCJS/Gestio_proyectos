
document.addEventListener('DOMContentLoaded', function () {

        // ===== NAVBAR SCROLL EFFECT =====
        const navbar = document.getElementById('mainNav');
window.addEventListener('scroll', function () {
            if (window.scrollY > 20) {
    navbar.classList.add('scrolled');
            } else {
    navbar.classList.remove('scrolled');
            }
        });

// ===== ACTIVE NAV LINK ON SCROLL =====
const sections = document.querySelectorAll('section[id]');
const navLinks = document.querySelectorAll('.nav-link-mg');

const observerNav = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
        if (entry.isIntersecting) {
            const id = entry.target.getAttribute('id');
            navLinks.forEach(function (link) {
                link.classList.remove('active');
                if (link.getAttribute('href') === '#' + id) {
                    link.classList.add('active');
                }
            });
        }
    });
        }, {rootMargin: '-30% 0px -60% 0px' });

sections.forEach(function (section) {
    observerNav.observe(section);
        });

// ===== FADE UP ON SCROLL =====
const fadeElements = document.querySelectorAll('.fade-up');
const observerFade = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observerFade.unobserve(entry.target);
        }
    });
        }, {threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

fadeElements.forEach(function (el) {
    observerFade.observe(el);
        });

// ===== GENERATE HEAT MAP =====
var heatMap = document.getElementById('heatMap');
var heatColors = [
'#22C55E', '#22C55E', '#86EFAC',
'#F59E0B', '#F59E0B', '#FCD34D',
'#EF4444', '#F87171', '#F59E0B',
'#EF4444', '#DC2626', '#F59E0B',
'#86EFAC', '#FCD34D', '#22C55E',
'#FCD34D', '#EF4444', '#86EFAC',
'#22C55E', '#22C55E'
];
heatColors.forEach(function (color) {
            var cell = document.createElement('div');
cell.className = 'heat-cell';
cell.style.backgroundColor = color;
cell.style.opacity = '0.85';
heatMap.appendChild(cell);
        });

// ===== GENERATE BAR CHART =====
var barChart = document.getElementById('barChart');
var barData = [
{height: '35%', color: '#22C55E' },
{height: '60%', color: '#F59E0B' },
{height: '80%', color: '#F97316' },
{height: '95%', color: '#EF4444' }
];
barData.forEach(function (bar) {
            var el = document.createElement('div');
el.className = 'mini-bar';
el.style.height = bar.height;
el.style.backgroundColor = bar.color;
barChart.appendChild(el);
        });

// ===== GENERATE RISK LIST =====
var riskList = document.getElementById('riskList');
var risks = [
{name: 'Acceso no autorizado', pct: 88, color: '#EF4444' },
{name: 'Pérdida de datos', pct: 72, color: '#F97316' },
{name: 'Ataque phishing', pct: 65, color: '#F59E0B' },
{name: 'Fallo de servicio', pct: 48, color: '#F59E0B' },
{name: 'Fuga información', pct: 32, color: '#22C55E' }
];
risks.forEach(function (risk) {
            var item = document.createElement('div');
item.className = 'risk-item';
item.innerHTML =
'<span class="risk-dot" style="background:' + risk.color + '"></span>' +
'<span style="flex:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">' + risk.name + '</span>' +
'<span style="font-weight:600; font-size:0.62rem; color:var(--slate-500); min-width:28px; text-align:right;">' + risk.pct + '</span>' +
'<div class="risk-bar-bg"><div class="risk-bar-fill" style="width:0%; background:' + risk.color + ';" data-width="' + risk.pct + '%"></div></div>';
riskList.appendChild(item);
        });

// ===== ANIMATE RISK BARS ON SCROLL =====
var riskSection = document.querySelector('.hero-illustration');
var barsAnimated = false;

var observerBars = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
        if (entry.isIntersecting && !barsAnimated) {
            barsAnimated = true;
            var fills = document.querySelectorAll('.risk-bar-fill');
            fills.forEach(function (fill, i) {
                setTimeout(function () {
                    fill.style.width = fill.getAttribute('data-width');
                }, 300 + (i * 150));
            });
        }
    });
        }, {threshold: 0.3 });

if (riskSection) {
    observerBars.observe(riskSection);
        }

// ===== CLOSE MOBILE NAV ON LINK CLICK =====
var navbarCollapse = document.getElementById('navbarContent');
var navLinksAll = navbarCollapse.querySelectorAll('.nav-link-mg');
navLinksAll.forEach(function (link) {
    link.addEventListener('click', function () {
        var bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse);
        if (bsCollapse) {
            bsCollapse.hide();
        }
    });
        });
    });
