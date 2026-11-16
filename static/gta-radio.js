/* ===== Radio synthwave generada por código para Mi ERP =====
   No reproduce ningún archivo de audio ni canción existente: todos los
   sonidos se sintetizan en vivo con la Web Audio API (osciladores +
   ruido blanco para el hi-hat). Por eso no hay ningún tema de copyright. */

(function () {
  if (document.querySelector('.gta-radio')) return;

  var ESTACIONES = [
    { nombre: 'FLASH 88.3', bpm: 96,  raiz: 220.00, escala: [0, 3, 5, 7, 10], onda: 'sawtooth' }, // atardecer, melancólico
    { nombre: 'NEON 102.7', bpm: 118, raiz: 174.61, escala: [0, 2, 4, 7, 9],  onda: 'square'   }, // arcade, animado
    { nombre: 'MIDNIGHT FM', bpm: 84, raiz: 196.00, escala: [0, 3, 7, 10, 12], onda: 'sine'    }  // nocturno, suave
  ];

  var ctx = null, master = null, filtro = null, timer = null;
  var estacionActual = 0, paso = 0, sonando = false;

  function asegurarContexto() {
    if (ctx) return;
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    master = ctx.createGain();
    master.gain.value = 0.22;
    filtro = ctx.createBiquadFilter();
    filtro.type = 'lowpass';
    filtro.frequency.value = 2200;
    master.connect(filtro).connect(ctx.destination);
  }

  function nota(freqBase, semitono) {
    return freqBase * Math.pow(2, semitono / 12);
  }

  // un "pluck" de sintetizador: oscilador + envolvente corta
  function pluck(freq, inicio, duracion, onda, volumen) {
    var osc = ctx.createOscillator();
    var g = ctx.createGain();
    osc.type = onda;
    osc.frequency.value = freq;
    g.gain.setValueAtTime(0, inicio);
    g.gain.linearRampToValueAtTime(volumen, inicio + 0.015);
    g.gain.exponentialRampToValueAtTime(0.0001, inicio + duracion);
    osc.connect(g).connect(master);
    osc.start(inicio);
    osc.stop(inicio + duracion + 0.05);
  }

  // pad largo y suave de fondo (acorde sostenido)
  function pad(freqs, inicio, duracion) {
    freqs.forEach(function (f) {
      var osc = ctx.createOscillator();
      var g = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = f;
      g.gain.setValueAtTime(0, inicio);
      g.gain.linearRampToValueAtTime(0.05, inicio + 0.6);
      g.gain.linearRampToValueAtTime(0, inicio + duracion);
      osc.connect(g).connect(master);
      osc.start(inicio);
      osc.stop(inicio + duracion + 0.1);
    });
  }

  // hi-hat: ruido blanco filtrado en agudos, muy corto
  function hihat(inicio, volumen) {
    var dur = 0.045;
    var buffer = ctx.createBuffer(1, ctx.sampleRate * dur, ctx.sampleRate);
    var data = buffer.getChannelData(0);
    for (var i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    var ruido = ctx.createBufferSource();
    ruido.buffer = buffer;
    var pasaAltos = ctx.createBiquadFilter();
    pasaAltos.type = 'highpass';
    pasaAltos.frequency.value = 7000;
    var g = ctx.createGain();
    g.gain.setValueAtTime(volumen, inicio);
    g.gain.exponentialRampToValueAtTime(0.0001, inicio + dur);
    ruido.connect(pasaAltos).connect(g).connect(master);
    ruido.start(inicio);
  }

  // kick sintetizado: oscilador grave con caída rápida de frecuencia
  function kick(inicio) {
    var osc = ctx.createOscillator();
    var g = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(130, inicio);
    osc.frequency.exponentialRampToValueAtTime(42, inicio + 0.12);
    g.gain.setValueAtTime(0.5, inicio);
    g.gain.exponentialRampToValueAtTime(0.0001, inicio + 0.16);
    osc.connect(g).connect(master);
    osc.start(inicio);
    osc.stop(inicio + 0.2);
  }

  function programarCompas() {
    var est = ESTACIONES[estacionActual];
    var corchea = 60 / est.bpm / 2;
    var ahora = ctx.currentTime + 0.05;

    // pad de acorde cada 8 pasos (un compás largo)
    if (paso % 8 === 0) {
      var acorde = [0, est.escala[2], est.escala[4] - 12].map(function (s) {
        return nota(est.raiz, s);
      });
      pad(acorde, ahora, corchea * 8);
    }

    // línea de bajo tipo arpegio, un paso de la escala por corchea
    var semitonoBajo = est.escala[paso % est.escala.length] - 12;
    pluck(nota(est.raiz, semitonoBajo), ahora, corchea * 0.9, est.onda, 0.14);

    // melodía ligera cada 2 pasos, una octava arriba, patrón simple
    if (paso % 2 === 0) {
      var i = Math.floor(paso / 2) % est.escala.length;
      pluck(nota(est.raiz, est.escala[i] + 12), ahora + corchea * 0.1, corchea * 1.4, est.onda, 0.09);
    }

    // batería: kick en el pulso, hi-hat en cada corchea
    if (paso % 4 === 0) kick(ahora);
    hihat(ahora, paso % 2 === 0 ? 0.12 : 0.06);

    paso = (paso + 1) % 64;
    timer = setTimeout(programarCompas, corchea * 1000);
  }

  function iniciar() {
    asegurarContexto();
    if (ctx.state === 'suspended') ctx.resume();
    paso = 0;
    sonando = true;
    programarCompas();
  }
  function detener() {
    sonando = false;
    clearTimeout(timer);
  }

  // ---- interfaz ----
  var el = document.createElement('div');
  el.className = 'gta-radio';
  el.innerHTML =
    '<button class="gta-radio__play" type="button" aria-label="Reproducir radio">▶</button>' +
    '<div class="gta-radio__info">' +
      '<span class="gta-radio__station"></span>' +
      '<span class="gta-radio__hint">Radio generada en vivo</span>' +
    '</div>' +
    '<div class="gta-radio__bars"><span></span><span></span><span></span><span></span></div>' +
    '<input class="gta-radio__vol" type="range" min="0" max="100" value="22" aria-label="Volumen">' +
    '<button class="gta-radio__next" type="button" aria-label="Siguiente estación">⏭</button>';
  document.body.appendChild(el);

  var btnPlay  = el.querySelector('.gta-radio__play');
  var btnNext  = el.querySelector('.gta-radio__next');
  var vol      = el.querySelector('.gta-radio__vol');
  var nombreEl = el.querySelector('.gta-radio__station');

  function pintarEstacion() { nombreEl.textContent = ESTACIONES[estacionActual].nombre; }
  pintarEstacion();

  btnPlay.addEventListener('click', function () {
    if (sonando) {
      detener();
      btnPlay.textContent = '▶';
      btnPlay.setAttribute('aria-label', 'Reproducir radio');
      el.classList.remove('is-playing');
    } else {
      iniciar();
      btnPlay.textContent = '❚❚';
      btnPlay.setAttribute('aria-label', 'Pausar radio');
      el.classList.add('is-playing');
    }
  });

  btnNext.addEventListener('click', function () {
    estacionActual = (estacionActual + 1) % ESTACIONES.length;
    pintarEstacion();
    if (sonando) { clearTimeout(timer); paso = 0; programarCompas(); }
  });

  vol.addEventListener('input', function () {
    if (master) master.gain.value = vol.value / 100 * 0.45;
  });
})();