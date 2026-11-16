(function () {
  if (document.querySelector('.gta-scene')) return;
  var root = document.documentElement;

  function skyline() {
    var seed = 7, x = 0, d = '';
    function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
    while (x < 1200) {
      var w = 22 + rnd() * 48, h = 30 + rnd() * 150;
      d += 'M' + x + ' 200 V' + (200 - h) + ' h' + w + ' V200 Z ';
      if (rnd() > 0.7) d += 'M' + (x + w / 2 - 2) + ' ' + (200 - h) + ' v-' + (10 + rnd() * 25) + ' h4 v20 Z ';
      x += w + rnd() * 6;
    }
    return '<svg class="gta-skyline" viewBox="0 0 1200 200" preserveAspectRatio="none"><path d="' + d + '"/></svg>';
  }

  function palm(cls) {
    var leaves = [-165, -135, -105, -75, -45, -15, 15, 45, 75].map(function (a) {
      return '<path transform="rotate(' + a + ')" d="M0 0 C25 -38 78 -38 112 18 C78 -10 35 -10 0 0Z"/>';
    }).join('');
    return '<svg class="gta-palm ' + cls + '" viewBox="0 0 260 420" aria-hidden="true">' +
      '<path d="M96 420 C101 310 112 210 122 124 L131 124 C122 216 113 312 112 420Z"/>' +
      '<g transform="translate(126 120)">' + leaves + '</g></svg>';
  }

  var scene = document.createElement('div');
  scene.className = 'gta-scene';
  scene.setAttribute('aria-hidden', 'true');
  scene.innerHTML =
    '<div class="gta-rays"></div><div class="gta-glow"></div><div class="gta-sun"></div>' +
    skyline() + '<div class="gta-ground"></div>' + palm('l') + palm('r') +
    '<div class="gta-vignette"></div><div class="gta-grain"></div>';
  document.body.insertBefore(scene, document.body.firstChild);

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!reduce) {
    window.addEventListener('pointermove', function (e) {
      root.style.setProperty('--mx', (e.clientX / innerWidth - 0.5).toFixed(3));
      root.style.setProperty('--my', (e.clientY / innerHeight - 0.5).toFixed(3));
    }, { passive: true });
  }
})();