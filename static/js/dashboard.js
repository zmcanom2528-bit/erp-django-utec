/* Gráficas del dashboard (Chart.js). Lee los datos de #dash-data y se
   repinta cuando cambia el tema claro/oscuro. */
(function () {
    var nodo = document.getElementById('dash-data');
    if (!nodo || typeof Chart === 'undefined') return;
    var d = JSON.parse(nodo.textContent), graficas = [];

    function css(v) {
        return getComputedStyle(document.documentElement).getPropertyValue(v).trim();
    }
    function rgba(hex, a) {
        var n = parseInt(hex.slice(1), 16);
        return 'rgba(' + (n >> 16) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
    }
    function dinero(v) { return '$' + Number(v).toLocaleString('es-MX', { maximumFractionDigits: 2 }); }

    function pintar() {
        graficas.forEach(function (g) { g.destroy(); });
        graficas = [];
        Chart.defaults.color = css('--clr-muted');
        Chart.defaults.font.family = 'Inter, sans-serif';
        var rejilla = css('--clr-border'), a1 = css('--accent'), a2 = css('--accent-2');

        function crear(id, cfg) {
            var c = document.getElementById(id);
            if (c) graficas.push(new Chart(c, cfg));
        }
        var base = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } };

        // Unidades en stock por categoría (barras horizontales)
        crear('chStock', {
            type: 'bar',
            data: { labels: d.stock.labels, datasets: [{
                data: d.stock.data, borderRadius: 4, barThickness: 12,
                backgroundColor: [a1, a2, '#ff8566', '#ffb199', '#5b5b6b'] }] },
            options: Object.assign({}, base, { indexAxis: 'y', scales: {
                x: { grid: { color: rejilla }, ticks: { font: { size: 10 }, precision: 0 } },
                y: { grid: { display: false }, ticks: { font: { size: 10 } } } } })
        });

        // Clientes activos acumulados
        crear('chClientes', {
            type: 'line',
            data: { labels: d.clientes.labels, datasets: [{
                data: d.clientes.data, borderColor: a1, borderWidth: 2, fill: true,
                backgroundColor: rgba(a1.length === 7 ? a1 : '#ff3b30', .18),
                tension: .4, pointRadius: 2 }] },
            options: Object.assign({}, base, { scales: {
                x: { grid: { display: false }, ticks: { font: { size: 10 } } },
                y: { display: false, beginAtZero: true } } })
        });

        // Ingresos por día
        crear('chVentas', {
            type: 'line',
            data: { labels: d.ventas.labels, datasets: [{
                data: d.ventas.data, borderColor: a2, borderWidth: 2.5, fill: true,
                backgroundColor: rgba(a2.length === 7 ? a2 : '#ff5e36', .18),
                tension: .4, pointRadius: 2 }] },
            options: Object.assign({}, base, {
                plugins: { legend: { display: false },
                           tooltip: { callbacks: { label: function (c) { return dinero(c.parsed.y); } } } },
                scales: { x: { grid: { display: false }, ticks: { font: { size: 10 } } },
                          y: { display: false, beginAtZero: true } } })
        });

        // Ingresos por categoría
        crear('chCats', {
            type: 'doughnut',
            data: { labels: d.categorias.labels, datasets: [{
                data: d.categorias.data, backgroundColor: d.categorias.colors,
                borderColor: css('--clr-surface'), borderWidth: 2 }] },
            options: Object.assign({}, base, { cutout: '68%',
                plugins: { legend: { display: false },
                           tooltip: { callbacks: { label: function (c) { return c.label + ': ' + dinero(c.parsed); } } } } })
        });
    }

    pintar();
    document.addEventListener('erp:theme', pintar);
})();
