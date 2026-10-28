/* Tema claro/oscuro y menú móvil. */
(function () {
    var html = document.documentElement;
    var btn  = document.getElementById('themeBtn');

    function pintar(tema) {
        html.setAttribute('data-theme', tema);
        if (!btn) return;
        btn.textContent = tema === 'dark' ? '☀️' : '🌙';
        btn.setAttribute('aria-label',
            tema === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro');
    }
    pintar(html.getAttribute('data-theme') || 'dark');

    if (btn) {
        btn.addEventListener('click', function () {
            var nuevo = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            pintar(nuevo);
            try { localStorage.setItem('erpTheme', nuevo); } catch (e) {}
            document.dispatchEvent(new Event('erp:theme'));   // las gráficas se repintan
        });
    }

    var menuBtn = document.getElementById('menuBtn');
    var nav     = document.getElementById('mainNav');
    if (menuBtn && nav) {
        menuBtn.addEventListener('click', function () {
            var abierto = nav.classList.toggle('open');
            menuBtn.setAttribute('aria-expanded', abierto);
        });
    }
})();
